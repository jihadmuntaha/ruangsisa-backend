import jwt
import os
import random
import smtplib
from datetime import datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.models.activity_log import ActivityLog  # ◄ Tetap aman terjaga

# Setup context untuk hashing password menggunakan bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_secret_key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_SECONDS = int(os.getenv("JWT_EXPIRATION_SECONDS", 3600))


# ==========================================
# 🎫 JWT TOKEN HELPERS
# ==========================================

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Fungsi untuk men-generate token JWT dengan waktu kadaluarsa"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24) # Default kadaluarsa 24 jam
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


# ==========================================
# 🔐 SECURITY HELPERS (Password Hashing)
# ==========================================

def get_password_hash(password: str) -> str:
    """Mengubah password teks biasa menjadi hash acak yang aman"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Mengecek apakah password yang diinput cocok dengan yang ada di DB"""
    return pwd_context.verify(plain_password, hashed_password)


# ==========================================
# 📝 LOGGING HELPERS (Riwayat Aktivitas)
# ==========================================

def log_activity(db: Session, request: Request, activity: str, user_id: int = None, description: str = None):
    """
    Fungsi otomatis untuk mencatat log aktivitas pengguna ke database.
    Membaca IP Address dan User-Agent secara otomatis dari Request FastAPI.
    """
    ip_address = request.headers.get("x-forwarded-for") or (request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent")

    db_log = ActivityLog(
        user_id=user_id,
        activity=activity,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


# ==========================================
# 📧 OTP & SMTP EMAIL HELPERS (NEW ADDITION)
# ==========================================

def generate_otp() -> str:
    """Fungsi pembuat 6-digit angka acak untuk OTP"""
    return str(random.randint(100000, 999999))


def send_otp_email(target_email: str, otp_code: str, purpose: str) -> bool:
    """
    Fungsi pengirim email asli via SMTP Gmail.
    Pastikan lu dapet App Password 16 digit dari Google Account lu, Beh!
    """
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "jihadnaks@gmail.com"  # ◄ Gunakan email lu
    sender_password = "ohcuhsdshbxiikzx"      # ◄ ISI PAKE 16 DIGIT APP PASSWORD GMAIL LU!

    # Tentukan subjek email berdasarkan kebutuhan pintu login
    if purpose == "register":
        subject = "Kode OTP RuangSisa - Verifikasi Akun Baru"
    else:
        subject = "Kode OTP RuangSisa - Reset Password Akun"
    
    # Desain bodi email HTML elegan nuansa hijau khas RuangSisa
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style='color: #2D6A4F;'>Halo Kontributor RuangSisa!</h2>
            <p>Terima kasih telah berkontribusi menjaga bumi melalui sirkulasi ekonomi bijak.</p>
            <p>Berikut adalah 6-digit kode rahasia OTP lu:</p>
            <div style='font-size: 26px; font-weight: bold; color: #0F5238; letter-spacing: 6px; padding: 12px 24px; background-color: #E8FFF0; display: inline-block; border-radius: 8px; border: 1px solid #95D4B3; margin: 15px 0;'>
                {otp_code}
            </div>
            <p style='color: #C1121F; font-size: 13px; font-weight: bold;'>*Kode ini hanya berlaku selama 10 menit. Jangan pernah berikan kode ini kepada siapapun!</p>
            <br>
            <p style="font-size: 11px; color: #777;">Salam ramah lingkungan,<br><b>Tim Pengembang RuangSisa</b></p>
        </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = f"RuangSisa Official <{sender_email}>"
    msg['To'] = target_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Amankan jalur pipa SMTP
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, target_email, msg.as_string())
        server.quit()
        print(f"🚀 [SMTP SUCCESS] Berhasil meledakkan email OTP ke {target_email}")
        return True
    except Exception as e:
        print(f"🚨 [SMTP ERROR] Gagal mengirim paket email: {e}")
        return False