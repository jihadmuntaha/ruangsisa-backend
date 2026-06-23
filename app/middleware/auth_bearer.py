# app/middleware/auth_bearer.py
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.models.user import User as UserModel
from sqlalchemy.orm import Session
from app.config.database import get_db
from fastapi import Depends

security = HTTPBearer()

# 🟢 PERBAIKAN SAKLAK: Ganti SECRET_KEY menjadi JWT_SECRET agar dicintai auth.py
JWT_SECRET = "fallback_secret_key" 
ALGORITHM = "HS256"

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Skema autentikasi harus Bearer!")
            
            token = credentials.credentials
            return self.verify_jwt(token)
        else:
            raise HTTPException(status_code=403, detail="Token autentikasi tidak ditemukan!")

    # 🟢 PERBAIKAN TIPE DATA: Ubah type hint kembalian dari 'str' menjadi 'dict' (karena payload berupa JSON/Dict)
    def verify_jwt(self, jwtoken: str) -> dict:
        try:
            payload = jwt.decode(jwtoken, JWT_SECRET, algorithms=[ALGORITHM])
            
            # 🖥️ DEBUG TERMINAL: Biar lu bisa ngelihat isi payload asli buatan file login lu!
            print(f"==================================================")
            print(f"📡 [DEBUG PAYLOAD BACKEND] Isi token lu: {payload}")
            print(f"==================================================")
            
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Sesi login telah kedaluwarsa, Beh!")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Sesi login tidak valid atau telah berakhir!")


def get_current_user(token: dict = Depends(JWTBearer()), db: Session = Depends(get_db)):
    # Jika token bernilai None atau False karena tidak lolos validasi di atas
    if not token:
        raise HTTPException(status_code=401, detail="Token tidak sah atau payload kosong!")
    
    # 🟢 SAKTI & ADAPTIF: Skenario baca klaim ID user secara fleksibel agar lolos dari jeratan 'Token tidak sah!'
    user_id = token.get("user_id") or token.get("id") or token.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=401, 
            detail=f"Token berhasil didekripsi, tapi backend gak nemu key 'user_id' atau 'id' di payload: {token}"
        )
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User pemilik token tidak ditemukan di database!")
    
    return user