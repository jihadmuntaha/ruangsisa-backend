from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# ==========================================
# USER SCHEMAS
# ==========================================

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
    avatar: Optional[str] = None  # Tambahan untuk menampung URL foto profil Google
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

# Skema request untuk update profile
class UserUpdateProfile(BaseModel):
    name: str
    bio: Optional[str] = None
    location: Optional[str] = None

# Skema response setelah sukses update
class UserProfileResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    bio: Optional[str]
    location: Optional[str]
    avatar: Optional[str] = None  # Tambahan agar sinkron
    eco_points: int

    class Config:
        from_attributes = True


# ==========================================
# ACTIVITY LOG SCHEMAS (Fitur Baru)
# ==========================================

# Schema untuk menampilkan riwayat log ke client/Flutter jika dibutuhkan nanti
class ActivityLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    activity: str
    description: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True