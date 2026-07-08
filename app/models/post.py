from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class CategoryModel(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_name = Column(String(50), nullable=False)
    icon_name = Column(String(50), nullable=False)

    posts = relationship("PostModel", back_populates="category")


class PostModel(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    images = Column(Text, nullable=True)
    post_type = Column(Enum("Barter", "Dijual", "Donasi", name="jenis_layanan"), nullable=False)
    price = Column(Integer, nullable=True)
    barter_wishlist = Column(String(255), nullable=True)
    status = Column(Enum("pending", "approved", "rejected", name="textile_status"), default="pending")
    created_at = Column(TIMESTAMP, server_default=func.now())

    # ✅ RELATIONSHIP
    author = relationship("User", back_populates="posts", foreign_keys=[user_id])
    category = relationship("CategoryModel", back_populates="posts")
    
    # ✅ TAMBAHKAN INI - relationship ke comments
    comments = relationship("CommentModel", back_populates="post", cascade="all, delete-orphan")

    # ✅ TAMBAHKAN INI - relationship ke interactions
    # interactions = relationship("InteractionModel", back_populates="post", cascade="all, delete-orphan")