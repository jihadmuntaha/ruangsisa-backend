from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.user import User as UserModel # Sesuaikan dengan path model lu
from app.schemas.user import UserUpdateProfile, UserProfileResponse
from app.middleware.auth_bearer import get_current_user # Sesuaikan fungsi guard JWT lu

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.put("/profile", response_model=UserProfileResponse)
def update_profile(
    profile_data: UserUpdateProfile, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user) # Kunci pengaman token JWT
):
    try:
        # Update field data di objek model user yang sedang login
        current_user.name = profile_data.name
        current_user.bio = profile_data.bio
        current_user.location = profile_data.location
        
        # Commit perubahan ke database Supabase
        db.commit()
        db.refresh(current_user)
        
        return current_user
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memperbarui profil: {str(e)}"
        )