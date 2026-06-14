import jwt
import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models.activity_log import ActivityLog
from fastapi import Request

# Setup context untuk hashing password menggunakan bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_secret_key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_SECONDS = int(os.getenv("JWT_EXPIRATION_SECONDS", 3600))

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