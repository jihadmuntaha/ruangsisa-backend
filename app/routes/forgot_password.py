from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta
import random

from app.config.database import get_db 
from app.models.user import User 
from app.models.otp import OTPVerification  # 🟢 Kelas model asli database lu
from app.utils import get_jakarta_time, get_password_hash, send_otp_email # 🟢 Fungsi email ijo lu

router = APIRouter(prefix="/api/auth/forgot-password", tags=["Forgot Password"])

class RequestOtpSchema(BaseModel):
    email: EmailStr

class VerifyOtpSchema(BaseModel):
    email: EmailStr
    otp: str

class ResetPasswordSchema(BaseModel):
    email: EmailStr
    otp: str
    new_password: str
from datetime import datetime, timedelta # 🟢 Pastikan datetime diimport murni

# ================= 🔥 TAHAP 1: REQUEST OTP (FIXED UTC TIME) =================
@router.post("/request")
def request_otp(payload: RequestOtpSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email tidak terdaftar, Beh!")
    
    generated_otp = str(random.randint(1000, 9999)) # Genap 4 Digit sesuai Flutter
    
    db.query(OTPVerification).filter(
        OTPVerification.email == payload.email,
        OTPVerification.purpose == "forgot_password",
        OTPVerification.is_used == False
    ).update({"is_used": True})
    
    # 🟢 SAKRAL: Kita simpan pakai utcnow() biar serasi sama jam bawaan Supabase Cloud!
    db_otp = OTPVerification(
        email=payload.email,
        otp_code=generated_otp,
        purpose="forgot_password",  
        is_used=False,
        expired_at=datetime.utcnow() + timedelta(minutes=10) # Valid 10 menit UTC
    )
    db.add(db_otp)
    db.commit()
    
    print(f"📡 [SMTP START] Mengirim OTP Lupa Sandi ke {payload.email}...")
    email_sent = send_otp_email(payload.email, generated_otp, purpose="forgot_password")
    
    if not email_sent:
        raise HTTPException(status_code=500, detail="Gagal menyambungkan pipa SMTP Google.")
    
    return {"status": "success", "message": "Kode OTP pemulihan berhasil dikirim! 🚀"}


# ================= 🔥 TAHAP 2: VERIFIKASI KODE OTP (FIXED UTC TIME) =================
@router.post("/verify")
def verify_otp(payload: VerifyOtpSchema, db: Session = Depends(get_db)):
    db_otp = db.query(OTPVerification).filter(
        OTPVerification.email == payload.email,
        OTPVerification.otp_code == payload.otp,
        OTPVerification.purpose == "forgot_password",
        OTPVerification.is_used == False
    ).order_by(OTPVerification.id.desc()).first()
        
    if not db_otp:
        raise HTTPException(status_code=400, detail="Kode OTP yang Anda masukkan salah, Beh!")
        
    # 🟢 SAKRAL: Bandingkan murni menggunakan waktu netral server UTC vs UTC
    now_utc = datetime.utcnow()
    expired_utc = db_otp.expired_at.replace(tzinfo=None) if db_otp.expired_at.tzinfo else db_otp.expired_at
        
    if now_utc > expired_utc:
        raise HTTPException(status_code=400, detail="Kode OTP sudah kedaluwarsa, silakan minta kode baru.")
        
    return {"status": "success", "detail": "OTP Valid"}


# ================= 🔥 TAHAP 3: UPDATE PASSWORD BARU (FIXED UTC TIME) =================
@router.post("/reset")
def reset_password(payload: ResetPasswordSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
        
    db_otp = db.query(OTPVerification).filter(
        OTPVerification.email == payload.email,
        OTPVerification.otp_code == payload.otp,
        OTPVerification.purpose == "forgot_password",
        OTPVerification.is_used == False
    ).order_by(OTPVerification.id.desc()).first()
        
    if not db_otp:
        raise HTTPException(status_code=400, detail="Sesi pemulihan tidak valid.")
        
    # 🟢 SAKRAL: Pengecekan keamanan akhir pakai standar UTC murni
    now_utc = datetime.utcnow()
    expired_utc = db_otp.expired_at.replace(tzinfo=None) if db_otp.expired_at.tzinfo else db_otp.expired_at
        
    if now_utc > expired_utc:
        raise HTTPException(status_code=400, detail="Sesi pemulihan sudah habis masanya.")
        
    user.password = get_password_hash(payload.new_password)
    db_otp.is_used = True
    db.commit()
    return {"status": "success", "message": "Kata sandi akun Anda berhasil diperbarui!"}