from sqlalchemy import Column, Integer, String, Text, Enum, DECIMAL, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class CategoryModel(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_name = Column(String(50), nullable=False)
    icon_name = Column(String(50), nullable=False) # Menyimpan string nama icon untuk Flutter

    # Relationship ke tabel posts
    posts = relationship("PostModel", back_populates="category")


class PostModel(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    
    # --- PERBAIKAN DI SINI: 'namee' diubah menjadi 'name' ---
    post_type = Column(Enum("Barter", "Dijual", "Donasi", name="jenis_layanan"), nullable=False)
    
    price = Column(DECIMAL(10, 2), nullable=True) # Hanya terisi jika post_type = 'Dijual'
    barter_wishlist = Column(String(255), nullable=True) # Hanya terisi jika post_type = 'Barter'
    
    # Ini sudah benar
    status = Column(Enum("pending", "approved", "rejected", name="textile_status"), default="pending")
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relasi ORM (Eager Loading ready untuk JSON GetX)
    author = relationship("UserModel")
    category = relationship("CategoryModel", back_populates="posts")