from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Schema untuk menerima data dari Flutter (Request)
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

# Schema untuk mengembalikan data ke Flutter (Response)
class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    bio: Optional[str] = None
    location: Optional[str] = None
    eco_points: int
    created_at: datetime

    class Config:
        from_attributes = True


# Schema untuk menerima data login dari Flutter
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Schema untuk mengirim balik Token JWT ke Flutter
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse  # Menyertakan info user dasar biar Flutter bisa langsung pakai data profil