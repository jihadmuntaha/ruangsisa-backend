from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os
import shutil
import jwt

from app.config.database import get_db
from app.models.user import User
from app.models.otp import OTPVerification  
from app.schemas.user import UserRegister, UserResponse, UserLogin, TokenResponse
from app.schemas.otp import OTPVerify, OTPResend  
from app.utils import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    log_activity,
    generate_otp,       
    send_otp_email      
)
from app.utils_face import get_face_embedding, compare_faces
from app.middleware.auth_bearer import get_current_user, JWT_SECRET, ALGORITHM  # ◄ FIXED: Gunakan fungsi asli lu!
from typing import List

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

TEMP_DIR = "temp_faces"
os.makedirs(TEMP_DIR, exist_ok=True)

# =========================================================================
# 📝 1. ENDPOINT REGISTER (Suntikan BackgroundTasks - Anti-Delay)
# =========================================================================
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserRegister, 
    request: Request, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
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
        eco_points=0,
        is_verified=False  
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # GENERATE OTP
    otp_code = generate_otp()
    db_otp = OTPVerification(email=new_user.email, otp_code=otp_code, purpose="register")
    db.add(db_otp)
    db.commit()
    
    # Lempar fungsi kirim email ke Background Task (Respons langsung 201 ke Flutter!)
    background_tasks.add_task(send_otp_email, new_user.email, otp_code, "register")
    
    log_activity(
        db=db, request=request, user_id=new_user.id, activity="Register Akun",
        description=f"User {new_user.name} mendaftar lokal. Pengiriman paket email didelegasikan ke background thread."
    )
    
    return new_user


# =========================================================================
# 🔐 2. ENDPOINT LOGIN LOKAL (Proteksi Gembok Verifikasi OTP)
# =========================================================================
@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email atau password salah!")
    
    if not user.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Akun ini terdaftar via Google. Silakan login menggunakan Google!"
        )
    
    if not verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email atau password salah!")
    
    # PROTEKSI SAKLEK: Cegah login jika akun belum melakukan aktivasi kode OTP
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun lu belum aktif, Beh! Silakan verifikasi kode OTP di email lu duluan."
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    log_activity(
        db=db, request=request, user_id=user.id, activity="Login Lokal",
        description=f"User {user.name} berhasil masuk aplikasi."
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


# =========================================================================
# 🌐 3. ENDPOINT GOOGLE AUTH (Auto-Bypass OTP Karena Terverifikasi Google)
# =========================================================================
@router.post("/google", response_model=TokenResponse)
def google_auth(payload: dict, request: Request, db: Session = Depends(get_db)):
    token_dari_flutter = payload.get("id_token")
    if not token_dari_flutter:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google ID Token tidak ditemukan!")
        
    try:
        id_info = id_token.verify_oauth2_token(token_dari_flutter, google_requests.Request())
        token_audience = id_info.get("aud")
        
        if token_audience != GOOGLE_CLIENT_ID:
            raise ValueError("Audience token tidak cocok!")
            
        email = id_info.get("email")
        name = id_info.get("name")
        avatar = id_info.get("picture")
        google_id = id_info.get("sub")
        
    except ValueError as e:
        print(f" 🔥 [GOOGLE AUTH ERROR]: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google ID Token tidak valid atau sudah kadaluarsa! Detail: {str(e)}"
        )
        
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # GOOGLE BYPASS: Otomatis aktifkan status karena Google sudah menjamin keaslian email
        user = User(
            name=name, email=email, avatar=avatar, google_id=google_id,
            eco_points=0, is_verified=True, verified_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        log_activity(
            db=db, request=request, user_id=user.id, activity="Register Google",
            description=f"User {user.name} otomatis terdaftar & langsung aktif via Google."
        )
    else:
        if not user.google_id:
            user.google_id = google_id
            user.is_verified = True  
            db.commit()
            db.refresh(user)
            
        log_activity(
            db=db, request=request, user_id=user.id, activity="Login Google",
            description=f"User {user.name} masuk menggunakan Google."
        )
        
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


# =========================================================================
# 📡 4. ENDPOINT VERIFIKASI OTP REALTIME FROM FLUTTER
# =========================================================================
@router.post("/verify-otp")
def verify_otp(payload: OTPVerify, request: Request, db: Session = Depends(get_db)):
    print(f"📡 [BACKEND] Mencoba verifikasi OTP untuk email: {payload.email}")
    
    db_otp = db.query(OTPVerification).filter(
        OTPVerification.email == payload.email,
        OTPVerification.otp_code == payload.otp_code,
        OTPVerification.purpose == payload.purpose,
        OTPVerification.is_used == False,
        OTPVerification.expired_at > datetime.utcnow()
    ).order_by(OTPVerification.id.desc()).first()

    if not db_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kode OTP keliru, sudah kedaluwarsa, atau sudah terpakai, Beh!"
        )

    db_otp.is_used = True
    
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Data user kontributor tidak ditemukan!")
    
    user.is_verified = True
    user.verified_at = datetime.utcnow()
    db.commit()

    log_activity(
        db=db, request=request, user_id=user.id, activity="Verifikasi OTP Sukses",
        description=f"User {user.name} sukses mengaktifkan akun via verifikasi OTP ({payload.purpose})."
    )
    
    return {"status": "success", "message": "Selamat, verifikasi berhasil dilakukan!"}


# =========================================================================
# 🔥 5. ENDPOINT KIRIM ULANG OTP (BackgroundTasks - Anti-Freezing)
# =========================================================================
@router.post("/resend-otp")
def resend_otp(
    payload: OTPResend, 
    request: Request, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email jahanam ini belum terdaftar di RuangSisa!")

    db.query(OTPVerification).filter(
        OTPVerification.email == payload.email,
        OTPVerification.purpose == payload.purpose
    ).update({"is_used": True})

    new_otp = generate_otp()
    db_otp = OTPVerification(email=payload.email, otp_code=new_otp, purpose=payload.purpose)
    db.add(db_otp)
    db.commit()

    # Delegasikan tugas pengiriman email kirim ulang ke background thread
    background_tasks.add_task(send_otp_email, payload.email, new_otp, payload.purpose)

    log_activity(
        db=db, request=request, user_id=user.id, activity="Resend OTP",
        description=f"User {user.name} meminta kirim ulang OTP untuk keperluan {payload.purpose}."
    )

    return {"status": "success", "message": "Kode OTP baru sedang dikirim ke email lu!"}


# =========================================================================
# 👤🔒 API DAFTAR WAJAH PREMIUM (MENYELURUH SE-MUKA SEPERTI APPLE FACE ID)
# =========================================================================
@router.post("/register-face-premium")
async def register_face_premium(
    email: str,
    files: List[UploadFile] = File(...), # ◄ MENERIMA MULTIPLE FILE FOTO
    db: Session = Depends(get_db)
):
    # 1. Cari kontributor berdasarkan email form register
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email belum terdaftar, Beh!")

    all_embeddings = []

    # 2. Iterasi dan ekstrak setiap sudut wajah yang dikirim Flutter
    for idx, file in enumerate(files):
        file_path = os.path.join(TEMP_DIR, f"multi_{idx}_{email}_{file.filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Ekstrak matriks menggunakan OpenCV Haar Cascade kita
        embedding_json = get_face_embedding(file_path)
        
        if os.path.exists(file_path):
            os.remove(file_path) # Bersihkan file mentah gambar

        if embedding_json:
            all_embeddings.append(embedding_json)

    # Jika dari semua sampel foto tidak ada satu pun wajah yang lolos sensor OpenCV
    if not all_embeddings:
        raise HTTPException(
            status_code=400,
            detail="OpenCV gagal mendeteksi wajah di semua sampel foto. Cari tempat terang, Beh!"
        )

    # 3. Kunci Barisan Array Koordinat Wajah Menyeluruh ke Database
    # Kita bungkus list embeddings ke string JSON agar masuk aman ke kolom TEXT SQLite
    import json
    user.face_embedding = json.dumps(all_embeddings)
    db.commit()

    return {
        "status": "success",
        "message": f"Premium Face ID untuk {email} sukses dikunci dari berbagai sudut! 👤🔒🔥"
    }

import json

# =========================================================================
# 🔴 7. API LOGIN INSTAN MULTI-ANGLE (MENDUKUNG FORMAT FACE ID PREMIUM)
# =========================================================================
@router.post("/login-face")
async def login_with_face(
    email: str, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email belum terdaftar di RuangSisa!")
        
    if not user.face_embedding:
        raise HTTPException(status_code=400, detail="Akun lu belum mengaktifkan Face ID!")
    
    # Simpan foto login sementara dari HP Realme lu
    file_path = os.path.join(TEMP_DIR, f"login_{email}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Membongkar string array kumpulan sudut wajah dari DB
    try:
        saved_embeddings = json.loads(user.face_embedding)
    except Exception:
        # Fallback jika data lama berbentuk string tunggal biasa
        saved_embeddings = [user.face_embedding]
        
    # LOOPING CHECK: Cocokkan foto baru dengan seluruh sudut wajah yang ada di database
    is_match = False
    for single_embedding in saved_embeddings:
        # Kita gunakan threshold=0.15 agar pencocokan korelasi matriks OpenCV lebih responsif
        if compare_faces(single_embedding, file_path, threshold=0.15):
            is_match = True
            break # Jika salah satu sudut (depan/kiri/kanan) cocok, langsung lulus sensor!
            
    if os.path.exists(file_path):
        os.remove(file_path)
        
    if not is_match:
        raise HTTPException(status_code=401, detail="Verifikasi Gagal! Sudut wajah lu gak sinkron, Beh.")
        
    # JIKA LULUS: Cetak token akses JWT resmi RuangSisa untuk dilempar balik ke Flutter
    expire = datetime.utcnow() + timedelta(days=1)
    payload = {"user_id": user.id, "email": user.email, "exp": expire}
    access_token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
        
    return {
        "status": "success",
        "message": "Autentikasi Biometrik Berhasil! Selamat Datang, Beh! 🍏🟢",
        "token": access_token
    }