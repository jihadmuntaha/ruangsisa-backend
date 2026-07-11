import json
import os
import shutil
import random
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import db
from firebase_admin import db
import httpx
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.user import User as UserModel 
from app.models.activity_log import ActivityLog 
from app.schemas.user import UserUpdateProfile, UserProfileResponse
from app.middleware.auth_bearer import get_current_user 
from passlib.context import CryptContext 
import supabase as supabase_  # 🟢 Import resmi Supabase SDK

# Setup password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 🟢 PREFIX TETAP "/user" SESUAI ASLI LU, BEH!
router = APIRouter(prefix="/user", tags=["Users"])

# 🟢 Inisialisasi Client Resmi via Environment Variable Vercel
SUPABASE_URL = os.environ.get("SUPABASE_URL")
# Pake Service Role Key biar backend lu punya hak mutlak bypass RLS saat upload
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") 

supabase: supabase_.Client = supabase_.create_client(SUPABASE_URL, SUPABASE_KEY)

# 🟢 SOLUSI KUNCI MEMORI: Bungkus dalam class static agar state aman, konsisten, & gak hilang antar-request
class OtpMemory:
    storage = {}

# =======================================================================
# 👤 0. ENDPOINT SEARCH KONTRIBUTOR (SINKRON DENGAN SEARCH VIEW FLUTTER)
# =======================================================================
# 🟢 OPSI AMAN: Kembalikan ke string kosong murni agar jalurnya mengikat ke root prefix "/user"
@router.get("", status_code=status.HTTP_200_OK)
def search_contributors(
    search: Optional[str] = Query(None, description="Cari nama kontributor spesifik"),
    db: Session = Depends(get_db)
):
    print("📡 [GET /user] Endpoint search kontributor berhasil ditembak!")
    try:
        query = db.query(UserModel)
        
        if search and search.strip() != "":
            search_text = f"%{search.strip()}%"
            query = query.filter(UserModel.name.like(search_text))
            print(f"👤 [FASTAPI USER SEARCH] Menyaring nama: {search}")
            
        users = query.order_by(UserModel.id.desc()).limit(50).all()
        print(f"✅ Menemukan total {len(users)} user di database SQLite.")
        
        results = []
        for u in users:
            display_avatar = u.avatar if u.avatar else ""
            if display_avatar and not display_avatar.startswith("/static/"):
                if display_avatar.startswith("user_"):
                    display_avatar = f"/static/avatars/{display_avatar}"

            results.append({
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "avatar": display_avatar,
                "bio": u.bio if u.bio else "",
                "location": u.location if u.location else ""
            })
        return results
    except Exception as e:
        print(f"❌ Gagal mengambil data user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        # 🟢 JALUR AMAN: Jangan blokir content_type dari Flutter
        # Kita deteksi tipenya, kalau aneh/kosong kita default-kan ke image/jpeg
        c_type = file.content_type if file.content_type else "image/jpeg"
        
        # Tentukan ekstensi file untuk disimpan di Supabase
        extension = "png" if "png" in c_type.lower() else "jpg"

        # Baca file langsung dari memory RAM
        content = await file.read()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"user_{current_user.id}_{timestamp}.{extension}"
        storage_path = f"profiles/{filename}"

        # Kirim resmi via SDK Supabase
        supabase.storage.from_("avatars").upload(
            path=storage_path,
            file=content,
            file_options={"content-type": c_type} # Gunakan tipe konten yang sudah disaring
        )

        public_avatar_url = supabase.storage.from_("avatars").get_public_url(storage_path)

        current_user.avatar = public_avatar_url
        db.commit()
        db.refresh(current_user)

        return {"status": "success", "avatar": public_avatar_url}

    except Exception as e:
        db.rollback()
        print(f"🚨 [AVATAR UPLOAD ERROR]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Gagal upload avatar ke Cloud: {str(e)}")
    
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

        is_google_user = current_user.google_id is not None and (not current_user.password)

        if not is_google_user:
            if not old_password:
                raise HTTPException(status_code=400, detail="Kata sandi lama wajib diisi untuk akun manual!")
            if not pwd_context.verify(old_password, current_user.password):
                raise HTTPException(status_code=400, detail="Kata sandi lama salah, Beh!")
        
        otp_code = str(random.randint(1000, 9999))
        expiry_time = datetime.now() + timedelta(minutes=5)
        
        OtpMemory.storage[current_user.email] = {
            "otp": otp_code,
            "expiry": expiry_time,
            "new_password_hash": pwd_context.hash(new_password)
        }

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
        user_otp_data = OtpMemory.storage.get(current_user.email)

        if not user_otp_data:
            raise HTTPException(status_code=400, detail="Sesi OTP tidak ditemukan atau silakan request dari awal, Beh!")

        if datetime.now() > user_otp_data["expiry"]:
            OtpMemory.storage.pop(current_user.email, None) 
            raise HTTPException(status_code=400, detail="Kode OTP sudah kadaluwarsa, Beh! Silakan minta kode baru.")

        if input_otp != user_otp_data["otp"]:
            raise HTTPException(status_code=400, detail="Kode OTP salah, Beh!")

        current_user.password = user_otp_data["new_password_hash"]
        db.commit()

        OtpMemory.storage.pop(current_user.email, None)

        return {"status": "success", "detail": "Kata sandi sukses diperbarui berlapis OTP!"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal memverifikasi OTP: {str(e)}")

# =======================================================================
# 4. ENDPOINT LOG AKTIVITAS (YANG SUDAH STERIL & USER-FRIENDLY)
# =======================================================================
@router.get("/logs")
def get_user_activity_logs(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user) 
):
    try:
        print(f"📡 [GET /user/logs] Menarik log steril untuk User ID: {current_user.id}")
        
        # 1. Tarik semua log miliki user terlebih dahulu
        logs = db.query(ActivityLog).filter(
            ActivityLog.user_id == current_user.id
        ).order_by(ActivityLog.id.desc()).all() # ◄ GANTI .created_at JADI .id DI SINI
        
        formatted_logs = []
        for log in logs:
            activity_name = log.activity or ""
            
            # 🟢 SENSOR PINTAR VERSI KEDUA (LEBIH AKURAT):
            # Ubah ke lowercase dulu biar pencarian teksnya gak sensitif huruf kapital
            act_lower = activity_name.lower()
            
            # Jika ini log sistem (mengandung "/" atau "fcm-token") DAN BUKAN bagian dari manajemen kain perca
            if ("/" in act_lower or "fcm-token" in act_lower) and ("manajemen" not in act_lower):
                continue # ✂️ Buang log sampah sistem, tapi loloskan Manajemen Kain Perca!
                
            try:
                details_obj = json.loads(log.description) if log.description else {}
            except Exception:
                details_obj = {"info": log.description}
                
            formatted_logs.append({
                "id": log.id,
                "user_id": log.user_id,
                "activity": activity_name, 
                "action": activity_name,   
                "details": details_obj,
                "created_at": log.created_at.isoformat() if log.created_at else ""
            })
            
        print(f"✅ Berhasil mengirim {len(formatted_logs)} log steril ke Flutter.")
        return formatted_logs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()