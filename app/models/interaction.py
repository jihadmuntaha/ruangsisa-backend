# app/models/interaction.py (atau nama file model lu)
from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, Boolean, String, DateTime
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base
from app.utils import get_jakarta_time

class CommentModel(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=get_jakarta_time)

    # Relationships
    post = relationship("PostModel", back_populates="comments")
    user = relationship("User", back_populates="comments")


class ChatRoomModel(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_one_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_two_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    last_message = Column(Text, nullable=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 🟢 PERBAIKAN SAKTI: Definisikan relasi ke User secara spesifik agar SQLAlchemy tidak bingung
    user_one = relationship("User", foreign_keys=[user_one_id], overlaps="chat_rooms_v1")
    user_two = relationship("User", foreign_keys=[user_two_id], overlaps="chat_rooms_v2")

    # 🔗 Relasi ke isi pesan
    messages = relationship("MessageModel", back_populates="room", cascade="all, delete-orphan")


class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_text = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=get_jakarta_time)

    # 🔗 Relasi balik ke room
    room = relationship("ChatRoomModel", back_populates="messages")
    
    # 🟢 Relasi ke User pengirim pesan
    sender = relationship("User", foreign_keys=[sender_id])


# class InteractionModel(Base):
#     __tablename__ = "interactions"

#     id = Column(Integer, primary_key=True, index=True, autoincrement=True)
#     post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
#     interaction_type = Column(String(50), nullable=False, default="like")
#     created_at = Column(TIMESTAMP, server_default=func.now())

#     # 🟢 HUBUNGAN RELASI AMAN (Menggunakan Target String Nama Kelas)
#     post = relationship("PostModel", back_populates="interactions")
#     user = relationship("User", back_populates="interactions")