from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.config.database import get_db
from app.models.post import PostModel
from app.models.user import User
from app.models.interaction import CommentModel
from datetime import datetime

# 🟢 SUNTIKKAN IMPORT HELPER FCM DI SINI
from app.helpers.notification import send_fcm_notification

router = APIRouter(prefix="/api", tags=["Interactions"])

# ✅ GET COMMENTS BY POST ID
@router.get("/posts/{post_id}/comments")
def get_comments_by_post(
    post_id: int,
    db: Session = Depends(get_db)
):
    """
    Mendapatkan semua komentar untuk sebuah postingan
    """
    print(f"💬 [GET COMMENTS] Post ID: {post_id}")
    
    # Cek apakah post ada
    post = db.query(PostModel).filter(PostModel.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Postingan tidak ditemukan")
    
    # Ambil komentar
    comments = db.query(CommentModel).filter(CommentModel.post_id == post_id).order_by(CommentModel.created_at.desc()).all()
    
    result = []
    for comment in comments:
        user = db.query(User).filter(User.id == comment.user_id).first()
        result.append({
            "id": comment.id,
            "post_id": comment.post_id,
            "user_id": comment.user_id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
            "user": {
                "id": user.id if user else None,
                "name": user.name if user else "User Dihapus",
                "avatar": user.avatar if user else None
            }
        })
    
    print(f"✅ Returning {len(result)} comments")
    return result

# ✅ POST COMMENT - PERBAIKI WITH REAL-TIME NOTIFICATION
@router.post("/posts/comments", status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id: int = Form(...),   # ← Perhatikan nama field
    user_id: int = Form(...),   # ← Perhatikan nama field
    content: str = Form(...),   # ← Perhatikan nama field
    db: Session = Depends(get_db),
):
    """
    Membuat komentar baru pada postingan
    """
    try:
        print("=" * 50)
        print(f"💬 [CREATE COMMENT]")
        print(f"   - post_id: {post_id}")
        print(f"   - user_id: {user_id}")
        print(f"   - content: {content}")
        print("=" * 50)
        
        # Validasi post
        post = db.query(PostModel).filter(PostModel.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Postingan tidak ditemukan")
        
        # Validasi user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        
        # Validasi content
        if not content or len(content.strip()) == 0:
            raise HTTPException(status_code=422, detail="Komentar tidak boleh kosong")
        
        # Create comment
        new_comment = CommentModel(
            post_id=post_id,
            user_id=user_id,
            content=content.strip()
        )
        
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)
        
        print(f"✅ Comment created! ID: {new_comment.id}")
        
        # 🟢 SUNTIKKAN FITUR LOGIKA NOTIFIKASI FCM DI SINI
        try:
            # Ambil data pemilik postingan asli (penerima notifikasi)
            post_owner = db.query(User).filter(User.id == post.user_id).first()
            
            # Kirim notif hanya jika pengomentar bukan pemilik postingan itu sendiri
            if post_owner and post_owner.id != user.id:
                if hasattr(post_owner, 'fcm_token') and post_owner.fcm_token:
                    print(f"🔔 [FCM] Mengirim notifikasi komentar ke {post_owner.name}...")
                    send_fcm_notification(
                        target_token=post_owner.fcm_token,
                        title="💬 Komentar Baru di Postingan Lu! 🎉",
                        body=f"{user.name} mengomentari postingan lu: \"{new_comment.content[:50]}\"",
                        data_payload={
                            "click_action": "FLUTTER_NOTIFICATION_CLICK",
                            "type": "comment",
                            "post_id": str(post_id)
                        }
                    )
                else:
                    print(f"⚠️ [FCM] Skip: User {post_owner.name} tidak memiliki fcm_token di database.")
        except Exception as fcm_err:
            print(f"🚨 [FCM ERROR] Gagal mengirim push notification: {fcm_err}")
        
        return {
            "id": new_comment.id,
            "post_id": new_comment.post_id,
            "user_id": new_comment.user_id,
            "content": new_comment.content,
            "created_at": new_comment.created_at.isoformat() if new_comment.created_at else None,
            "user": {
                "id": user.id,
                "name": user.name,
                "avatar": user.avatar
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# 🟢 ✅ DELETE COMMENT - SINKRONISASI FLUTTER REALME LU, BEH!
@router.delete("/posts/comments/{comment_id}", status_code=status.HTTP_200_OK)
def delete_comment_by_id(
    comment_id: int,
    user_id: int, # ◄ Menangkap query param '?user_id=4' dari Flutter lu
    db: Session = Depends(get_db)
):
    """
    Menghapus komentar berdasarkan ID komentar dan memvalidasi ID user pemiliknya
    """
    print(f"🗑️ [DELETE COMMENT] Mencoba menghapus Comment ID: {comment_id} oleh User ID: {user_id}")
    
    # 1. Cari data komentarnya di SQLite
    comment = db.query(CommentModel).filter(CommentModel.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Komentar ini tidak ditemukan atau sudah terhapus duluan, Beh!"
        )
    
    # 2. Validasi Keamanan: Pastikan user_id yang request cocok dengan pemilik komentar asli
    if comment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aksi ilegal! Lu gak boleh menghapus komentar kontributor lain, Beh!"
        )
    
    # 3. Ekstirpasi data dari database
    try:
        db.delete(comment)
        db.commit()
        print(f"✅ Comment ID {comment_id} sukses dihapus dari piringan hitam DB.")
        
        # Mengembalikan JSON respons sukses (Status 200) agar dibaca ijo royo-royo
        return {
            "status": "success",
            "message": "Komentar kain perca berhasil dimusnahkan!"
        }
    except Exception as e:
        db.rollback()
        print(f"❌ Gagal delete comment akibat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bentrok internal database: {str(e)}")