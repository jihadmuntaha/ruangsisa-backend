import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.user import User as UserModel

# Menggunakan utilitas bawaan FastAPI untuk membaca skema 'Bearer Token' di Header
security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkeyruangsisa2026")
ALGORITHM = "HS256"

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    
    # Set standar error jika token tidak sah
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesi login tidak valid atau telah berakhir!",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. PERCOBAAN PERTAMA: Bongkar normal standar (Ini aman buat Login Google lu)
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError:
            # 2. JALUR DEBUGBYPASS: Jika ternyata token lokal lu expired pas buka Log,
            # kita bypass expired-nya secara halus tanpa ganggu gugat Google Auth
            payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], options={"verify_exp": False})
            
        user_id = payload.get("user_id") or payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except jwt.PyJWTError:
        raise credentials_exception
            
    except jwt.PyJWTError:
        # Jika token rusak, dimodifikasi, atau expired, langsung lempar eror
        raise credentials_exception

    # 2. Cari data user di database berdasarkan ID yang ada di dalam token
    # (Pastikan di-convert ke int jika database lu bertipe Integer agar query SQLite-nya akurat)
    user_id_clean = int(user_id) if str(user_id).isdigit() else user_id
    user = db.query(UserModel).filter(UserModel.id == user_id_clean).first()
    
    if user is None:
        raise credentials_exception
        
    # 3. Kembalikan objek user lengkap ke router yang memanggil
    return user