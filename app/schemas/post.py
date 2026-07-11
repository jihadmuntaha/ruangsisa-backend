from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime

# 🌟 1. Skema Dasar untuk Menampung Input dari Flutter
class PostBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=150, description="Judul barang bekas")
    description: str = Field(..., min_length=10, description="Deskripsi kelayakan & minus barang")
    category_id: int = Field(..., description="ID kategori sehari-hari")
    post_type: str = Field(..., description="Wajib berisi: 'Barter', 'Dijual', atau 'Donasi'")
    price: Optional[int] = Field(None, description="Harga jika barang dijual")
    barter_wishlist: Optional[str] = Field(None, max_length=255, description="Barang yang diinginkan jika barter")
    images: Optional[str] = Field(None, description="String path foto produk (bisa dipisah koma)")

# 🛠️ 2. VALIDATOR PINTAR: Mengunci Aturan Main Sesuai Tipe Aksi
    @model_validator(mode="after")
    def validate_business_logic(self):
        # Aturan A: Jika Donasi, kunci harga ke 0 dan hapus wishlist barter
        if self.post_type == "Donasi":
            self.price = 0
            self.barter_wishlist = None
            
        # Aturan B: Jika Dijual, pastikan nominal harganya diisi dengan benar
        elif self.post_type == "Dijual":
            if self.price is None or self.price <= 0:
                raise ValueError("Untuk tipe aksi 'Dijual', nominal harga wajib diisi dan lebih dari Rp 0!")
            self.barter_wishlist = None
            
        # Aturan C: Jika Barter, pastikan wishlist barang penggantinya diisi
        elif self.post_type == "Barter":
            if not self.barter_wishlist or self.barter_wishlist.strip() == "":
                raise ValueError("Untuk tipe aksi 'Barter', kolom wishlist barang barteran wajib diisi!")
            self.price = None
            
        else:
            raise ValueError("Tipe aksi tidak valid! Harus: 'Barter', 'Dijual', atau 'Donasi'")
            
        return self


# 📥 3. Skema saat Flutter melakukan POST Request (Inherit dari Base)
class PostCreate(PostBase):
    pass


# 📤 4. Skema untuk Response API Balikan ke Flutter (Eager Loading Ready)
class UserInPost(BaseModel):
    id: int
    name: str
    avatar: Optional[str] = None

    class Config:
        from_attributes = True

class CategoryInPost(BaseModel):
    id: int
    category_name: str
    icon_name: str

    class Config:
        from_attributes = True

class PostResponse(BaseModel):
    id: int
    user_id: int
    category_id: int
    title: str
    description: str
    images: Optional[str] = None
    post_type: str
    price: Optional[int] = None
    barter_wishlist: Optional[str] = None
    status: str
    created_at: datetime
    
    # Menampilkan data relasi agar Flutter GetX tinggal pakai tanpa nembak API berulang-ulang
    author: UserInPost
    category: CategoryInPost

    class Config:
        from_attributes = True

class PostUpdate(BaseModel):
    title: str
    description: str
    post_type: str
    price: Optional[int] = None
    barter_wishlist: Optional[str] = None
    image_url: Optional[str] = None