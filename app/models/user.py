from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.config.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=True)  # Set True agar user Google tidak wajib punya password lokal
    bio = Column(Text, nullable=True)
    location = Column(String(100), nullable=True)
    avatar = Column(String(255), nullable=True)  # Untuk menyimpan URL foto profil dari Google
    eco_points = Column(Integer, default=0)
    google_id = Column(String(100), unique=True, index=True, nullable=True)  # ID unik dari Google OAuth
    
    # 🔥 TAMBAHAN UNTUK OTP VERIFICATION
    is_verified = Column(Boolean, default=False)  # Status verifikasi email
    verified_at = Column(DateTime, nullable=True)  # Waktu verifikasi
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🔗 Relasi tambahan untuk Chat & Message
    chat_rooms_v1 = relationship("ChatRoomModel", foreign_keys="[ChatRoomModel.user_one_id]")
    chat_rooms_v2 = relationship("ChatRoomModel", foreign_keys="[ChatRoomModel.user_two_id]")

    # Relasi: Jika user dihapus, semua riwayat log aktivitasnya juga ikut terhapus
    logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")

    # Relasi ke tabel posts (1 user bisa punya banyak post)
    posts = relationship("PostModel", back_populates="author", cascade="all, delete-orphan")

    # Relasi ke tabel comments (1 user bisa punya banyak komentar)
    comments = relationship("CommentModel", back_populates="user", cascade="all, delete-orphan")