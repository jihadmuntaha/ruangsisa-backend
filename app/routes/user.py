import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.user import User as UserModel 
from app.models.activity_log import ActivityLog # ◄ KUNCI: Import model log lu buat ditarik datanya
from app.schemas.user import UserUpdateProfile, UserProfileResponse
from app.middleware.auth_bearer import get_current_user 

# 🟢 SINKRONISASI PREFIX: Diubah jadi "/user" agar pas dengan tembakan http di Flutter lu, Beh!
router = APIRouter(prefix="/user", tags=["Users"])

# 1. ENDPOINT UPDATE PROFIL (YANG SUDAH LU PUNYA)
@router.put("/profile", response_model=UserProfileResponse)
def update_profile(
    profile_data: UserUpdateProfile, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user) 
):
    try:
        current_user.name = profile_data.name
        current_user.bio = profile_data.bio
        current_user.location = profile_data.location
        
        db.commit()
        db.refresh(current_user)
        
        return current_user
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memperbarui profil: {str(e)}"
        )

# Pastikan bentuknya seperti ini di dalam app/routes/user.py:
# app/routes/user.py

@router.get("/logs")
def get_user_activity_logs(
    db: Session = Depends(get_db),
    # 🟢 KUNCI: Ubah dari 'User' menjadi 'UserModel' (sesuai alias import di file lu)
    current_user: UserModel = Depends(get_current_user) 
):
    try:
        # Ambil log yang murni milik user yang sedang login saat ini
        logs = db.query(ActivityLog).filter(ActivityLog.user_id == current_user.id).order_by(ActivityLog.created_at.desc()).all()
        
        formatted_logs = []
        for log in logs:
            try:
                # Kolom asli DB lu adalah description, bukan details!
                details_obj = json.loads(log.description) if log.description else {}
            except Exception:
                details_obj = {"info": log.description}
                
            formatted_logs.append({
                "id": log.id,
                "user_id": log.user_id,
                "action": log.activity, # ◄ Kolom asli DB lu adalah activity, bukan action!
                "details": details_obj,
                "created_at": log.created_at.isoformat() if log.created_at else ""
            })
            
        return formatted_logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memuat log aktivitas: {str(e)}")