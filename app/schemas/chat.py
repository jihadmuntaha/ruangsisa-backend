from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime

# 📥 1. Skema untuk membuat Room Chat baru
class ChatRoomCreate(BaseModel):
    receiver_id: int = Field(..., description="ID user lawan bicara yang mau diajak chat")


# 📥 2. Skema untuk mengirim pesan teks baru
class MessageCreate(BaseModel):
    chat_id: int = Field(..., description="ID room chat tujuan")
    message_text: str = Field(..., min_length=1, description="Isi pesan privat")


# 📤 3. Skema informasi User di dalam Chat (Pecahan Kontributor)
class UserInChat(BaseModel):
    id: int
    name: str
    avatar: Optional[str] = None

    class Config:
        from_attributes = True


# 📤 4. Skema balikan untuk isi pesan tunggal
class MessageResponse(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    message_text: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# 📤 5. Skema balikan untuk daftar Room Chat aktif (Chat List View di Flutter)
class ChatRoomResponse(BaseModel):
    id: int
    user_one_id: int
    user_two_id: int
    last_message: Optional[str] = None
    updated_at: Optional[datetime] = None
    # 🟢 SUNTIKAN SAKTI: Masukkan skema UserInChat sebagai receiver data lawan bicara!
    receiver: Optional[Any] = None
    unread_count: int = 0

    class Config:
        from_attributes = True