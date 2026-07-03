from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from app.config.database import get_db
from app.models.user import User as UserModel
from app.middleware.auth_bearer import get_current_user
from app.models.notification import NotificationModel
from app.services.fcm_service import send_push_notification


router = APIRouter(prefix="/api", tags=["Notifications"])

class FCMTokenRequest(BaseModel):
    fcm_token: str

# 🔒 1. ENDPOINT PENAMPUNG TOKEN (Biar Gak Eror 404 Lagi!)
@router.put("/users/fcm-token")
def update_fcm_token(
    payload: FCMTokenRequest, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    
    # Simpan token panjang dari HP Realme lu ke kolom fcm_token di DB
    user.fcm_token = payload.fcm_token
    db.commit()
    print(f"🔒 [FCM BACKEND] Token milik {user.name} sukses dikunci di DB SQLite!")
    return {"status": "success", "message": "Token sukses disinkronkan!"}


# 📜 2. ENDPOINT RIWAYAT NOTIFIKASI (Biar Gak Eror Null Lagi!)
@router.get("/notifications")
def get_my_notifications(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    # Ambil riwayat notifikasi asli milik user dari SQLite
    notifications = db.query(NotificationModel).filter(
        NotificationModel.user_id == current_user.id
    ).order_by(NotificationModel.created_at.desc()).all()
    
    return [
        {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "time": n.created_at.strftime("%H:%M") if n.created_at else "12:00",
            "is_read": "true" if n.is_read else "false",
            "type": n.type,
            "reference_id": n.reference_id
        } for n in notifications
    ]


# 🔓 3. ENDPOINT TANDAI DIBACA (Sudah Dilengkapi ke DB SQLite!)
@router.put("/notifications/{notif_id}/read")
def mark_notification_as_read(
    notif_id: int, # Diubah ke int menyesuaikan tipe ID SQLite pada umumnya
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    notif = db.query(NotificationModel).filter(
        NotificationModel.id == notif_id,
        NotificationModel.user_id == current_user.id
    ).first()
    
    if not notif:
        raise HTTPException(status_code=404, detail="Notifikasi tidak ditemukan, Beh!")
        
    notif.is_read = True
    db.commit()
    return {"status": "success", "message": "Notifikasi ditandai telah dibaca"}


# 🗑️ 4. ENDPOINT HAPUS NOTIFIKASI (Sudah Dilengkapi ke DB SQLite!)
@router.delete("/notifications/{notif_id}")
def delete_notification(
    notif_id: int, # Diubah ke int menyesuaikan tipe ID SQLite pada umumnya
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    notif = db.query(NotificationModel).filter(
        NotificationModel.id == notif_id,
        NotificationModel.user_id == current_user.id
    ).first()
    
    if not notif:
        raise HTTPException(status_code=404, detail="Notifikasi gagal dimusnahkan, data gaada!")
        
    db.delete(notif)
    db.commit()
    return {"status": "success", "message": "Notifikasi berhasil dimusnahkan"}

@router.post("/test-fcm-instant")
def test_fcm_instant(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    """
    Endpoint sakti untuk nembak langsung ke HP lu sendiri secara instan lewat Swagger!
    """
    if not current_user.fcm_token:
        raise HTTPException(status_code=400, detail="Token FCM lu belum tersimpan di DB, Beh!")
        
    status_kirim = send_push_notification(
        db=db,
        user_id=current_user.id,
        target_token=current_user.fcm_token,
        title="TES BOMBARDIR FCM 🚀",
        body="Kalau baris ini muncul, berarti pilar 3 backend & HP Realme lu udah tembus murni!",
        data_payload={"type": "test"}
    )
    
    return {"status": "executed", "gool": status_kirim}

@router.post("/test-fcm-instant-google")
def test_fcm_instant_google(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    """
    Endpoint pintas untuk nembak langsung ke HP sendiri via Swagger!
    """
    if not current_user.fcm_token:
        raise HTTPException(status_code=400, detail="Waduh Beh, token FCM lu belum kesimpen di DB!")
        
    print(f"🚀 [FCM SWAGGER] Mencoba nembak langsung ke User ID: {current_user.id} | Nama: {current_user.name}")
    
    status_kirim = send_push_notification(
        db=db,
        user_id=current_user.id,
        target_token=current_user.fcm_token,
        title="TES NOTIFIKASI GOOGLE SELESAI! 🚀",
        body="Pilar 3 Berhasil Total murni, Beh! Saatnya gas ke fitur Explore!",
        data_payload={"type": "test_instant"}
    )
    
    return {"status": "success", "fcm_sent": status_kirim}