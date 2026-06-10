import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.config.database import get_db
from app.models.user import UserModel
from app.schemas.user import UserRegister, UserResponse, UserLogin, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Konfigurasi hashing password menggunakan bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Konfigurasi JWT (Mengambil data dari file .env)
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkeyruangsisa2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # Token berlaku selama 24 jam (1 hari)

# --- FUNGSI UTALITAS: GENERATE JWT TOKEN ---
def create_access_token(data: dict):
    to_encode = data.copy()
    # Menentukan waktu kedaluwarsa token
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # Tanda tangani token digital dengan Secret Key
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

# --- ENDPOINT 1: REGISTER USER ---
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    # 1. Cek apakah email sudah terdaftar
    existing_user = db.query(UserModel).filter(UserModel.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar!"
        )
    
    # 2. Hash password sebelum disimpan
    hashed_password = pwd_context.hash(user_data.password)
    
    # 3. Buat objek user baru
    new_user = UserModel(
        name=user_data.name,
        email=user_data.email,
        password=hashed_password
    )
    
    # 4. Simpan ke database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

# --- ENDPOINT 2: LOGIN USER (BARU) ---
@router.post("/login", response_model=TokenResponse)
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    # 1. Cari user berdasarkan email di database
    user = db.query(UserModel).filter(UserModel.email == user_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Email atau kata sandi salah!"
        )
    
    # 2. Verifikasi kesesuaian password menggunakan passlib
    if not pwd_context.verify(user_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Email atau kata sandi salah!"
        )
    
    # 3. Masukkan payload data user ke dalam token
    token_payload = {"user_id": user.id, "email": user.email}
    access_token = create_access_token(data=token_payload)
    
    # 4. Return data lengkap dalam format JSON yang siap ditangkap GetX Flutter
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/forgot-password")
def forgot_password():
    pass

@router.post("/reset-password")
def reset_password():
    pass

@router.post("/google")
def google_login():
    pass