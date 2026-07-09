from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta
import random

from app.config.database import get_db 
from app.models.user import User 
# 🟢 1. SINKRON MURNI: Impor nama kelas asli bawaan database lu, Beh!
from app.models.otp import OTPVerification 
# 🟢 2. Impor helper email sakti nuansa hijau lu
from app.utils import get_jakarta_time, get_password_hash, send_otp_email 

router = APIRouter(prefix="/api/auth/forgot-password", tags=["Forgot Password"])

# --- 📋 PYDANTIC SCHEMAS UTK VALIDASI REQUEST ---
class RequestOtpSchema(BaseModel):
    email: EmailStr

class VerifyOtpSchema(BaseModel):
    email: EmailStr
    otp: str

class ResetPasswordSchema(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


# ================= 🔥 TAHAP 1: REQUEST OTP (FIXED MODEL CORRECTION) =================
@router.post("/request")
def request_otp(payload: RequestOtpSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alamat email tidak terdaftar dalam sistem RuangSisa, Beh!"
        )
    
    generated_otp = str(random.randint(100000, 999999))
    
    # 🟢 Hanguskan OTP forgot password lama milik email ini biar gak gantung
    db.query(OTPVerification).filter(
        OTPVerification.email == payload.email,
        OTPVerification.purpose == "forgot_password",
        OTPVerification.is_used == False
    ).update({"is_used": True})
    
    # 🟢 Simpan data baru ke model OTPVerification dengan mengunci purpose="forgot_password"
    db_otp = OTPVerification(
        email=payload.email,
        otp_code=generated_otp,
        purpose="forgot_password",  # ◄ PENENTU BIAR GAK TABRAKAN SAMA REGISTER!
        is_used=False,
        expired_at=get_jakarta_time() + timedelta(minutes=10)
    )
    db.add(db_otp)
    db.commit()
    
    # Jalankan ledakan SMTP murni secara synchronous biar gak freeze di Vercel Cloud
    print(f"📡 [SMTP START] Mengirim OTP Lupa Sandi ke {payload.email}...")
    email_sent = send_otp_email(payload.email, generated_otp, purpose="forgot_password")
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal menyambungkan pipa SMTP Google di awan Vercel, Beh!"
        )
    
    return {"status": "success", "message": "Kode OTP pemulihan berhasil dikirim ke email lu, Beh! 🚀"}


# ================= 🔥 TAHAP 2: VERIFIKASI KODE OTP =================
@router.post("/verify")
def verify_otp(payload: VerifyOtpSchema, db: Session = Depends(get_db)):
    # 🟢 Cari kodenya murni dari tabel OTPVerification dengan filter purpose khusus
    db_otp = db.query(OTPVerification).filter(
        OTPVerification.email == payload.email,
        OTPVerification.otp_code == payload.otp,
        OTPVerification.purpose == "forgot_password",
        OTPVerification.is_used == False
    ).order_by(OTPVerification.id.desc()).first()
        
    if not db_otp:
        raise HTTPException(status_code=400, detail="Kode OTP yang Anda masukkan salah, Beh!")
        
    if get_jakarta_time() > db_otp.expired_at:
        raise HTTPException(status_code=400, detail="Kode OTP sudah kedaluwarsa, silakan minta kode baru.")
        
    return {"status": "success", "detail": "OTP Valid"}


# ================= 🔥 TAHAP 3: UPDATE PASSWORD BARU =================
@router.post("/reset")
def reset_password(payload: ResetPasswordSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
        
    # 🟢 Amankan validasi ganda lewat model OTPVerification sebelum update password
    db_otp = db.query(OTPVerification).filter(
        OTPVerification.email == payload.email,
        OTPVerification.otp_code == payload.otp,
        OTPVerification.purpose == "forgot_password",
        OTPVerification.is_used == False
    ).order_by(OTPVerification.id.desc()).first()
        
    if not db_otp or get_jakarta_time() > db_otp.expired_at:
        raise HTTPException(status_code=400, detail="Sesi pemulihan tidak valid atau sudah habis.")
        
    # Hash password baru dan suntikkan ke tabel User
    user.password = get_password_hash(payload.new_password)
    
    # Hanguskan token OTP-nya biar gak disalahgunakan lagi
    db_otp.is_used = True
    
    db.commit()
    return {"status": "success", "message": "Kata sandi akun Anda berhasil diperbarui!"}