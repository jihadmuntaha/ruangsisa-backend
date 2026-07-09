from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta
import random

from app.config.database import get_db 
from app.models.user import User 
# 🟢 1. IMPORT MODEL TABEL BARU LU (Pastikan nama kelas modelnya sesuai, misal: OTPPassword)
from app.models.otp import OTPPassword 
# 🟢 2. IMPORT HELPER EMAIL ELEGANT LU
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


# ================= 🔥 TAHAP 1: REQUEST OTP (FIXED CLOUD & TABEL) =================
@router.post("/request")
def request_otp(payload: RequestOtpSchema, db: Session = Depends(get_db)):
    # 1. Pastikan email user terdaftar di sistem
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alamat email tidak terdaftar dalam sistem RuangSisa, Beh!"
        )
    
    # 2. Generate 6 digit kode OTP sesuai bawaan helper send_otp_email lu
    generated_otp = str(random.randint(100000, 999999))
    
    # 3. Matikan / Hanguskan OTP forgot password lama milik email ini agar tidak bentrok
    db.query(OTPPassword).filter(
        OTPPassword.email == payload.email,
        OTPPassword.is_used == False
    ).update({"is_used": True})
    
    # 4. Simpan data token baru murni ke tabel khusus: otp_password
    db_otp = OTPPassword(
        email=payload.email,
        otp_code=generated_otp,
        is_used=False,
        expired_at=get_jakarta_time() + timedelta(minutes=10) # Set 10 menit sesuai bodi HTML lu
    )
    db.add(db_otp)
    db.commit()
    
    # 5. JALUR SYNCHRONOUS SMTP GOOGLE ANTI-FREEZE VERCEL CLOUD
    # Kita panggil langsung fungsi template hijau lu dengan purpose="forgot_password"
    print(f"📡 [SMTP START] Mengirim OTP Lupa Sandi ke {payload.email}...")
    email_sent = send_otp_email(payload.email, generated_otp, purpose="forgot_password")
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal menyambungkan pipa SMTP Google di awan Vercel, Beh!"
        )
    
    return {"status": "success", "message": "Kode OTP pemulihan berhasil dikirim ke email lu, Beh! 🚀"}


# ================= 🔥 TAHAP 2: VERIFIKASI KODE OTP (FIXED TABEL) =================
@router.post("/verify")
def verify_otp(payload: VerifyOtpSchema, db: Session = Depends(get_db)):
    # 1. Bongkar dan cari kodenya murni dari tabel khusus otp_password
    db_otp = db.query(OTPPassword).filter(
        OTPPassword.email == payload.email,
        OTPPassword.otp_code == payload.otp,
        OTPPassword.is_used == False
    ).order_by(OTPPassword.id.desc()).first()
        
    if not db_otp:
        raise HTTPException(status_code=400, detail="Kode OTP yang Anda masukkan salah, Beh!")
        
    # 2. Validasi kedaluwarsa berbasis WIB
    if get_jakarta_time() > db_otp.expired_at:
        raise HTTPException(status_code=400, detail="Kode OTP sudah kedaluwarsa, silakan minta kode baru.")
        
    return {"status": "success", "detail": "OTP Valid"}


# ================= 🔥 TAHAP 3: UPDATE PASSWORD BARU (FIXED TABEL) =================
@router.post("/reset")
def reset_password(payload: ResetPasswordSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
        
    # 1. Validasi keamanan ganda lewat tabel otp_password sebelum eksekusi ganti sandi
    db_otp = db.query(OTPPassword).filter(
        OTPPassword.email == payload.email,
        OTPPassword.otp_code == payload.otp,
        OTPPassword.is_used == False
    ).order_by(OTPPassword.id.desc()).first()
        
    if not db_otp or get_jakarta_time() > db_otp.expired_at:
        raise HTTPException(status_code=400, detail="Sesi pemulihan tidak valid atau sudah habis.")
        
    # 2. Hash password baru dan simpan murni ke tabel User
    user.password = get_password_hash(payload.new_password)
    
    # 3. Kunci & hanguskan status OTP di tabel otp_password agar tidak bisa dipakai ulang (Exploit)
    db_otp.is_used = True
    
    db.commit()
    return {"status": "success", "message": "Kata sandi akun Anda berhasil diperbarui!"}