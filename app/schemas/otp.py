# app/schemas/otp.py
from pydantic import BaseModel, EmailStr

# 🟢 Schema khusus untuk nampung data pas pencet tombol "Verifikasi Kode"
class OTPVerify(BaseModel):
    email: EmailStr
    otp_code: str
    purpose: str  # Isinya wajib 'register' atau 'forgot_password'

    class Config:
        from_attributes = True


# 🟢 Schema khusus untuk nampung data pas pencet tombol "Kirim Ulang OTP"
class OTPResend(BaseModel):
    email: EmailStr
    purpose: str

    class Config:
        from_attributes = True