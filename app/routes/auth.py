import os
import jwt
import random
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import BaseModel, EmailStr

from app.config.database import get_db
from app.models.user import UserModel
from app.models.auth import OTPModel # Pastikan lu udah buat model ini di app/models/auth.py
from app.schemas.user import UserRegister, UserResponse, UserLogin, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Konfigurasi hashing password menggunakan bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Konfigurasi JWT (Mengambil data dari file .env)
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkeyruangsisa2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # Token berlaku selama 24 jam (1 hari)

# ⚙️ KONFIGURASI SMTP EMAIL
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)), # Default ke 587 jika di .env tidak diisi
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_FROM_NAME="RuangSisa Security Team",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# --- SKEMA PYDANTIC KHUSUS RESET PASSWORD ---
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str

# --- FUNGSI UTALITAS: GENERATE JWT TOKEN ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

# --- ENDPOINT 1: REGISTER USER ---
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(UserModel).filter(UserModel.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar!"
        )
    
    hashed_password = pwd_context.hash(user_data.password)
    
    new_user = UserModel(
        name=user_data.name,
        email=user_data.email,
        password=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

# --- ENDPOINT 2: LOGIN USER ---
@router.post("/login", response_model=TokenResponse)
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == user_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Email atau kata sandi salah!"
        )
    
    if not pwd_context.verify(user_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Email atau kata sandi salah!"
        )
    
    token_payload = {"user_id": user.id, "email": user.email}
    access_token = create_access_token(data=token_payload)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

# --- 🎯 ENDPOINT 3: REQUEST OTP (FORGOT PASSWORD) ---
@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # 1. Cek apakah email user terdaftar
    user = db.query(UserModel).filter(UserModel.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Email kontributor tidak terdaftar!"
        )

    # 2. Generate 6 digit angka OTP acak
    otp_code = f"{random.randint(100000, 999999)}"

    # 3. Simpan OTP ke database
    db_otp = OTPModel(email=request.email, otp_code=otp_code)
    db.add(db_otp)
    db.commit()

    # 4. Susun Template Email HTML RuangSisa yang Estetik
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px;">
        <h3 style="color: #2D6A4F;">Verifikasi Keamanan RuangSisa ♻️</h3>
        <p>Halo <b>{user.name}</b>, Anda telah meminta pengaturan ulang password akun kontributor.</p>
        <p>Berikut adalah kode OTP verifikasi Anda:</p>
        <div style="background-color: #f4f9f4; padding: 10px; text-align: center; border-radius: 5px;">
            <h2 style="color: #2D6A4F; letter-spacing: 5px; margin: 0;">{otp_code}</h2>
        </div>
        <p style="font-size: 12px; color: #666; margin-top: 15px;">Kode ini hanya berlaku selama <b>5 menit</b>. Jangan sebarkan kode ini kepada siapapun!</p>
    </div>
    """

    message = MessageSchema(
        subject="[RuangSisa] Kode OTP Reset Password Akun",
        recipients=[request.email],
        body=html,
        subtype=MessageType.html
    )

    # 5. Tembak kirim email secara asynchronous
    fm = FastMail(conf)
    await fm.send_message(message)

    return {"message": "Kode OTP berhasil dikirim ke email Anda!"}

# --- 🎯 ENDPOINT 4: VERIFIKASI OTP & RESET PASSWORD BARU ---
@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    # 1. Cari kode OTP paling baru di database berdasarkan email
    db_otp = db.query(OTPModel).filter(
        OTPModel.email == request.email,
        OTPModel.otp_code == request.otp_code
    ).order_by(OTPModel.created_at.desc()).first()

    if not db_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Kode OTP salah atau tidak valid!"
        )

    # 2. Cek apakah OTP sudah kadaluwarsa (lebih dari 5 menit) menggunakan timezone-aware UTC
    now_utc = datetime.now(timezone.utc)
    otp_time = db_otp.created_at.replace(tzinfo=timezone.utc) if db_otp.created_at.tzinfo is None else db_otp.created_at
    
    if now_utc - otp_time > timedelta(minutes=5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Kode OTP telah kadaluwarsa! Silahkan minta kode baru."
        )

    # 3. Cari usernya dan eksekusi ganti password
    user = db.query(UserModel).filter(UserModel.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User tidak ditemukan!"
        )

    # Hash password baru pake bcrypt sebelum disimpan
    user.password = pwd_context.hash(request.new_password)
    
    # Hapus OTP yang sudah terpakai dari DB biar bersih
    db.delete(db_otp)
    db.commit()

    return {"message": "Password akun RuangSisa Anda berhasil diperbarui! Silahkan login kembali."}

# --- ENDPOINT 5: GOOGLE LOGIN (NEXT FEATURE) ---
@router.post("/google")
def google_login():
    pass