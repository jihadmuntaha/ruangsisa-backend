from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.schemas.user import UserResponse # Mengabaikan info author dasar

# --- SCHEMA KATEGORI ---
class CategoryResponse(BaseModel):
    id: int
    category_name: str
    icon_name: str

    class Config:
        from_attributes = True

# --- SCHEMA POSTS ---
# Input dari Flutter saat bikin Post Baru
class PostCreate(BaseModel):
    category_id: int
    title: str
    description: str
    post_type: str # 'Barter', 'Dijual', 'Donasi'
    price: Optional[Decimal] = None
    barter_wishlist: Optional[str] = None

# Output JSON Response yang dilempar balik ke Flutter
class PostResponse(BaseModel):
    id: int
    title: str
    description: str
    post_type: str
    price: Optional[Decimal] = None
    barter_wishlist: Optional[str] = None
    status: str
    created_at: datetime
    category: CategoryResponse
    author: UserResponse

    class Config:
        from_attributes = True