from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# 🌟 Skema untuk menerima input dari Flutter
class CommentCreate(BaseModel):
    post_id: int = Field(..., description="ID postingan barang yang mau dikomentari/ditawar")
    comment_text: str = Field(..., min_length=1, description="Isi komentar atau nominal penawaran")

# 🌟 Skema untuk balikan data user di dalam komentar
class UserInComment(BaseModel):
    id: int
    name: str
    avatar: Optional[str] = None

    class Config:
        from_attributes = True

# 🌟 Skema response utuh untuk dilempar balik ke Flutter GetX
class CommentResponse(BaseModel):
    id: int
    post_id: int
    user_id: int
    comment_text: str
    created_at: datetime
    user: UserInComment  # ◄ Menyertakan info pengirim biar Flutter tinggal render nama & foto

    class Config:
        from_attributes = True