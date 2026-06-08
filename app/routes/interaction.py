from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from app.config.database import get_db
from app.middleware.auth_bearer import get_current_user
from app.models.user import UserModel
from app.models.interaction import CommentModel, ChatRoomModel, MessageModel
from app.schemas.interaction import CommentCreate, CommentResponse, MessageCreate

router = APIRouter(prefix="/api", tags=["Interactions (Comments & Chats)"])

# 1. Kirim Komentar Baru di Postingan Barang
@router.post("/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(data: CommentCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    new_comment = CommentModel(
        post_id=data.post_id,
        user_id=current_user.id,
        comment_text=data.comment_text
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment

# 2. Ambil Semua Komentar berdasarkan Post ID (Untuk feed Flutter)
@router.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
def get_post_comments(post_id: int, db: Session = Depends(get_db)):
    return db.query(CommentModel).filter(CommentModel.post_id == post_id).order_by(CommentModel.created_at.asc()).all()

# 3. Kirim Pesan / Buka Room Chat Personal Baru (DM)
@router.post("/chats/send")
def send_direct_message(data: MessageCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    if current_user.id == data.receiver_id:
        raise HTTPException(status_code=400, detail="Kamu tidak bisa mengechat dirimu sendiri!")

    # Cek apakah room chat antar kedua user ini sudah pernah ada sebelumnya
    room = db.query(ChatRoomModel).filter(
        or_(
            (ChatRoomModel.user_one_id == current_user.id) & (ChatRoomModel.user_two_id == data.receiver_id),
            (ChatRoomModel.user_one_id == data.receiver_id) & (ChatRoomModel.user_two_id == current_user.id)
        )
    ).first()

    # Jika belum ada room chat, otomatis buat room baru
    if not room:
        room = ChatRoomModel(user_one_id=current_user.id, user_two_id=data.receiver_id)
        db.add(room)
        db.commit()
        db.refresh(room)

    # Suntikkan pesan teks ke dalam room tersebut
    new_message = MessageModel(
        chat_id=room.id,
        sender_id=current_user.id,
        message_text=data.message_text
    )
    room.last_message = data.message_text  # Update preview teks terakhir di room
    
    db.add(new_message)
    db.commit()
    return {"status": "success", "message": "Pesan berhasil dikirim", "chat_id": room.id}