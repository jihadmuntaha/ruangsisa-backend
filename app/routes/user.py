import json
import os
import shutil
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.user import User as UserModel 
from app.models.activity_log import ActivityLog 
from app.schemas.user import UserUpdateProfile, UserProfileResponse
from app.middleware.auth_bearer import get_current_user 
from passlib.context import CryptContext 

# Setup password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 🟢 PREFIX TETAP "/user" SESUAI ASLI LU, BEH!
router = APIRouter(prefix="/user", tags=["Users"])

UPLOAD_DIR = "static/avatars"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 🟢 SOLUSI KUNCI MEMORI: Bungkus dalam class static agar state aman, konsisten, & gak hilang antar-request
class OtpMemory:
    storage = {}

# ==========================================
# 1. ENDPOINT UPDATE PROFIL (BAWAAN ASLI LU)
# ==========================================
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

# ==========================================
# 2. ENDPOINT UPLOAD AVATAR (BAWAAN ASLI LU)
# ==========================================
@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        extension = file.filename.split(".")[-1].lower()
        if extension not in ["jpg", "jpeg", "png"]:
            raise HTTPException(status_code=400, detail="Format file wajib JPG atau PNG, Beh!")

        filename = f"user_{current_user.id}_{int(os.path.getmtime(UPLOAD_DIR)) if os.path.exists(UPLOAD_DIR) else 1}.jpg"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        current_user.avatar = filename
        db.commit()
        db.refresh(current_user)

        return {"status": "success", "avatar": filename}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal upload avatar: {str(e)}")

# ========================================================
# 🔒 3A. FASE 1: REQUEST GANTI PASSWORD & KIRIM OTP
# ========================================================
@router.post("/change-password/request")
async def request_change_password(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        old_password = payload.get("old_password")
        new_password = payload.get("new_password")

        # 🟢 KUNCI USER GOOGLE: Cek apakah user ini terdaftar via Google (kolom google_id ada/tidak kosong) 
        # DAN password lamanya kosong atau belum pernah disetup
        is_google_user = current_user.google_id is not None and (not current_user.password)

        if not is_google_user:
            # Jika dia user manual, wajib verifikasi password lama seperti biasa
            if not old_password:
                raise HTTPException(status_code=400, detail="Kata sandi lama wajib diisi untuk akun manual!")
            if not pwd_context.verify(old_password, current_user.password):
                raise HTTPException(status_code=400, detail="Kata sandi lama salah, Beh!")
        
        # 2. Generate 4 digit kode OTP acak
        otp_code = str(random.randint(1000, 9999))
        expiry_time = datetime.now() + timedelta(minutes=5)
        
        # 3. Simpan state sementara ke memori static global
        OtpMemory.storage[current_user.email] = {
            "otp": otp_code,
            "expiry": expiry_time,
            "new_password_hash": pwd_context.hash(new_password)
        }

        # 4. SIMULASI KIRIM OTP
        print("\n" + "="*40)
        print(f"📩 [OTP RUANGSISA] Dikirim ke: {current_user.email}")
        print(f"🔑 KODE OTP ANDA: {otp_code}")
        print("="*40 + "\n")

        return {"status": "success", "detail": "Kode OTP konfirmasi telah dikirim!"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses request OTP: {str(e)}")

# ========================================================
# 🔒 3B. FASE 2: VERIFIKASI FINAL OTP & UPDATE DB 
# ========================================================
@router.post("/change-password/verify")
async def verify_change_password(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        input_otp = payload.get("otp")
        
        # Tarik data murni dari safe static memory storage
        user_otp_data = OtpMemory.storage.get(current_user.email)

        # 1. Validasi keberadaan sesi OTP (Sekarang aman dari bug thread reset)
        if not user_otp_data:
            raise HTTPException(status_code=400, detail="Sesi OTP tidak ditemukan atau silakan request dari awal, Beh!")

        # 2. Validasi kadaluwarsa masa berlaku OTP
        if datetime.now() > user_otp_data["expiry"]:
            OtpMemory.storage.pop(current_user.email, None) # Clear memory
            raise HTTPException(status_code=400, detail="Kode OTP sudah kadaluwarsa, Beh! Silakan minta kode baru.")

        # 3. Validasi kecocokan kode OTP
        if input_otp != user_otp_data["otp"]:
            raise HTTPException(status_code=400, detail="Kode OTP salah, Beh!")

        # 4. Jika lolos semua, eksekusi pembaruan password di database murni
        current_user.password = user_otp_data["new_password_hash"]
        db.commit()

        # Hapus data OTP dari memori (Single-use OTP Enforcement)
        OtpMemory.storage.pop(current_user.email, None)

        return {"status": "success", "detail": "Kata sandi sukses diperbarui berlapis OTP!"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal memverifikasi OTP: {str(e)}")

# ==========================================
# 4. ENDPOINT LOG AKTIVITAS (BAWAAN ASLI LU)
# ==========================================
@router.get("/logs")
def get_user_activity_logs(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user) 
):
    try:
        logs = db.query(ActivityLog).filter(ActivityLog.user_id == current_user.id).order_by(ActivityLog.created_at.desc()).all()
        
        formatted_logs = []
        for log in logs:
            try:
                details_obj = json.loads(log.description) if log.description else {}
            except Exception:
                details_obj = {"info": log.description}
                
            formatted_logs.append({
                "id": log.id,
                "user_id": log.user_id,
                "action": log.activity, 
                "details": details_obj,
                "created_at": log.created_at.isoformat() if log.created_at else ""
            })
            
        return formatted_logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memuat log aktivitas: {str(e)}")