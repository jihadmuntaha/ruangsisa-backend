from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.config.database import get_db
from app.models.interaction import CommentModel
from app.models.post import PostModel
from app.schemas.interaction import CommentCreate, CommentResponse
from app.middleware.auth_bearer import get_current_user
from app.models.user import User as UserModel

router = APIRouter(prefix="/api/interaction", tags=["Comments & Interaction"])

# 💬 1. Kirim Komentar / Penawaran Bidding Terbuka baru
@router.post("/posts/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    comment_data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user) # 🔐 Harus Login dulu
):
    # Cek dulu, barangnya beneran ada kagak di DB?
    post_exists = db.query(PostModel).filter(PostModel.id == comment_data.post_id).first()
    if not post_exists:
        raise HTTPException(status_code=404, detail="Postingan barang tidak ditemukan!")

    # Rakit komentar baru
    new_comment = CommentModel(
        post_id=comment_data.post_id,
        user_id=current_user.id, # Otomatis dari token JWT
        comment_text=comment_data.comment_text
    )

    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment


# 📜 2. Ambil semua list komentar berdasarkan ID Postingan (Buka Lembar Komentar di Flutter)
@router.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
def get_comments_by_post(post_id: int, db: Session = Depends(get_db)):
    # Cek apakah postingannya ada
    post_exists = db.query(PostModel).filter(PostModel.id == post_id).first()
    if not post_exists:
        raise HTTPException(status_code=404, detail="Postingan barang tidak ditemukan!")

    # Ambil semua komentar, urutkan dari yang paling lama (asc) agar logis dibaca dari atas ke bawah
    comments = db.query(CommentModel).filter(CommentModel.post_id == post_id).order_by(CommentModel.created_at.asc()).all()
    return comments