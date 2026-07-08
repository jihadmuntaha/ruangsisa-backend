from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta
import random

from app.config.database import get_db          # 👈 Sesuaikan path get_db lu
from app.models.user import User                  # 👈 Sesuaikan path model User lu
from app.utils import get_jakarta_time, get_password_hash # 👈 Ambil fungsi Jakarta & hash sandi lu

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


# ================= 🔥 TAHAP 1: REQUEST OTP =================
@router.post("/request")
def request_otp(payload: RequestOtpSchema, db: Session = Depends(get_db)):
    # 1. Pastikan email user terdaftar di sistem
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alamat email tidak terdaftar dalam sistem RuangSisa, Beh!"
        )
    
    # 2. Generate 4 digit kode OTP sesuai dengan form Flutter lu
    generated_otp = str(random.randint(1000, 9999))
    
    # 3. Masukkan OTP dan kunci waktu expired berbasis WIB (Waktu Sekarang + 5 Menit)
    user.otp_code = generated_otp
    user.otp_expires_at = get_jakarta_time() + timedelta(minutes=5)
    db.commit()
    
    # 4. PRINT DI TERMINAL BACKEND (Biar lu gampang copas OTP pas testing di emulator/postman)
    print(f"\n====================================================")
    print(f"📩 [OTP SERVER] Request Pemulihan Akun: {user.email}")
    print(f"🔑 KODE OTP AKTIF LU (WIB): {generated_otp}")
    print(f"⏰ KEDALUWARSA PADA: {user.otp_expires_at}")
    print(f"====================================================\n")
    
    # TODO: Kedepannya lu bisa pasang fungsi kirim email asli di sini (misal fastapi-mail)
    
    return {"message": "Kode OTP pemulihan berhasil dibuat."}


# ================= 🔥 TAHAP 2: VERIFIKASI KODE OTP =================
@router.post("/verify")
def verify_otp(payload: VerifyOtpSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
        
    # Validasi kesesuaian OTP
    if not user.otp_code or user.otp_code != payload.otp:
        raise HTTPException(status_code=400, detail="Kode OTP yang Anda masukkan salah, Beh!")
        
    # Validasi kedalwarsa menggunakan get_jakarta_time() murni WIB
    if get_jakarta_time() > user.otp_expires_at:
        raise HTTPException(status_code=400, detail="Kode OTP sudah kedaluwarsa, silakan minta kode baru.")
        
    return {"detail": "OTP Valid"}


# ================= 🔥 TAHAP 3: UPDATE PASSWORD BARU =================
@router.post("/reset")
def reset_password(payload: ResetPasswordSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
        
    # Validasi keamanan ekstra ganda sebelum eksekusi pergantian sandi
    if not user.otp_code or user.otp_code != payload.otp or get_jakarta_time() > user.otp_expires_at:
        raise HTTPException(status_code=400, detail="Sesi pemulihan tidak valid atau sudah habis.")
        
    # Hash password baru dan simpan ke database Supabase
    user.password = get_password_hash(payload.new_password)
    
    # Bersihkan kolom OTP agar token hangus dan tidak bisa dieksploitasi ulang
    user.otp_code = None
    user.otp_expires_at = None
    
    db.commit()
    return {"message": "Kata sandi akun Anda berhasil diperbarui!"}