from pydantic import BaseModel
from datetime import datetime
from app.schemas.user import UserResponse

class CommentCreate(BaseModel):
    post_id: int
    comment_text: str

class CommentResponse(BaseModel):
    id: int
    post_id: int
    comment_text: str
    created_at: datetime
    user: UserResponse

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    receiver_id: int  # ID User yang mau dichat pertama kali
    message_text: str