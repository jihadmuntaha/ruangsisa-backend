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
        # 1. Bongkar token JWT menggunakan Secret Key kita
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        
        if user_id is None:
            raise credentials_exception
            
    except jwt.PyJWTError:
        # Jika token rusak, dimodifikasi, atau expired, langsung lempar eror
        raise credentials_exception

    # 2. Cari data user di database berdasarkan ID yang ada di dalam token
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user is None:
        raise credentials_exception
        
    # 3. Kembalikan objek user lengkap ke router yang memanggil
    return user