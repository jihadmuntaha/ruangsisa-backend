from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserResponse
from app.utils import get_password_hash, log_activity
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserResponse, UserLogin, TokenResponse
from app.utils import get_password_hash, verify_password, create_access_token, log_activity
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegister, request: Request, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar!"
        )
    
    hashed_password = get_password_hash(payload.password)
    
    new_user = User(
        name=payload.name,
        email=payload.email,
        password=hashed_password,
        eco_points=0
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    log_activity(
        db=db,
        request=request,
        user_id=new_user.id,
        activity="Register Akun",
        description=f"User {new_user.name} berhasil mendaftar menggunakan email lokal."
    )
    
    return new_user


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    # 1. Cari user berdasarkan email
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah!"
        )
    
    # 2. Cek apakah user mendaftar lewat Google (tidak punya password lokal)
    if not user.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Akun ini terdaftar via Google. Silakan login menggunakan Google!"
        )
    
    # 3. Verifikasi password pencocokan hash
    if not verify_password(payload.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah!"
        )
    
    # 4. Generate token JWT RuangSisa jika sukses
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # 5. Catat riwayat ke Activity Log
    log_activity(
        db=db,
        request=request,
        user_id=user.id,
        activity="Login Lokal",
        description=f"User {user.name} berhasil login ke dalam aplikasi."
    )
    
    # 6. Kembalikan token beserta info data user sesuai TokenResponse schema
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


# Endpoint untuk Google Sign-In (Tukar Google ID Token dengan JWT RuangSisa)

@router.post("/google", response_model=TokenResponse)
def google_auth(payload: dict, request: Request, db: Session = Depends(get_db)):
    """Endpoint untuk menerima Google ID Token dari Flutter dan menukarnya dengan JWT RuangSisa"""
    
    # 1. Ambil token dari payload kiriman Flutter
    token_dari_flutter = payload.get("id_token")
    if not token_dari_flutter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID Token tidak ditemukan!"
        )
        
    try:
        # 2. Verifikasi token langsung ke Server Google (Tanpa clock_skew yang bikin crash)
        # Kita biarkan library memverifikasi struktur dasar tokennya dulu
        id_info = id_token.verify_oauth2_token(
            token_dari_flutter, 
            google_requests.Request()
        )
        
        # 🔍 VALIDASI AUDIENCE MANUAL (Multi-Platform & Anti-401)
        # Cara ini jauh lebih aman karena menerima token baik dari sisi Web App maupun Android
        token_audience = id_info.get("aud")
        
        # Jika token tidak cocok dengan Web Client ID kamu, kita validasi di sini
        if token_audience != GOOGLE_CLIENT_ID:
            # Opsional: Jika kamu ingin mengecek kecocokan dengan Android Client ID juga, buka baris di bawah:
            # if token_audience not in [GOOGLE_CLIENT_ID, "TARUH_CLIENT_ID_ANDROID_MU_JIKA_ADA"]:
            raise ValueError("Audience token tidak cocok dengan GOOGLE_CLIENT_ID backend!")
            
        # 3. Ekstrak data user yang dikembalikan oleh Google
        email = id_info.get("email")
        name = id_info.get("name")
        avatar = id_info.get("picture")
        google_id = id_info.get("sub") # ID unik user dari Google
        
    except ValueError as e:
        # 🛠️ TRICK SAKLEK: Cetak isi id_info mentah dari Google biar kelihatan ID aslinya
        # Kita pakai library jwt bawaan atau cetak error tokennya
        print(f" 🔥 [GOOGLE AUTH ERROR]: {str(e)}")
        
        # Tambahkan baris ini biar kita bisa tahu isi 'aud' yang dikirim HP Realme
        import json
        import base64
        try:
            # Membongkar isi token tanpa verifikasi cuma buat ngintip Client ID yang dikirim HP
            payload_b64 = token_dari_flutter.split('.')[1]
            payload_json = base64.b64decode(payload_b64 + '===').decode('utf-8')
            payload_data = json.loads(payload_json)
            print(f" 🔍 [CLIENT ID YANG DIKIRIM HP REALME]: {payload_data.get('aud')}")
        except:
            pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google ID Token tidak valid atau sudah kadaluarsa! Detail: {str(e)}"
        )
        
    # 4. Cek apakah user dengan email ini sudah ada di database RuangSisa
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Jika belum ada, otomatis daftarkan sebagai user baru via Google Login
        user = User(
            name=name,
            email=email,
            avatar=avatar,
            google_id=google_id,
            eco_points=0 # Poin awal sirkulasi ekonomi hijau
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        log_activity(
            db=db, request=request, user_id=user.id,
            activity="Register Google",
            description=f"User {user.name} otomatis terdaftar lewat Google Sign-In."
        )
    else:
        # Jika user sudah ada, update google_id-nya jika sebelumnya dia daftar lewat jalur lokal
        if not user.google_id:
            user.google_id = google_id
            db.commit()
            db.refresh(user)
            
        log_activity(
            db=db, request=request, user_id=user.id,
            activity="Login Google",
            description=f"User {user.name} berhasil masuk menggunakan akun Google."
        )
        
    # 5. Cetak JWT Token internal RuangSisa untuk hak akses Flutter
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user  # ◄ Ganti dictionary manual kemarin dengan objek 'user' langsung
    }