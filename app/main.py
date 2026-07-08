# =======================================================================
# 🟢 1. LOAD ENV DI KASTA TERTINGGI (WAJIB PALING ATAS SEBELUM IMPORT APP)
# =======================================================================
from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# Sekarang aman dimuat karena environment OS sudah memegang string Supabase!
from app.config.database import engine, Base, SessionLocal, FORCE_LOCAL_SQLITE
from app.middleware.activity_log import ActivityLogMiddleware

# =======================================================================
# 2. IMPORT MODELS DENGAN ALIAS
# =======================================================================
from app.models.post import CategoryModel
from app.models.user import User
from app.models.activity_log import ActivityLog
from app.models import interaction as m_interaction
from app.models import auth as m_auth
from app.models.notification import NotificationModel

# 3. Import Routers untuk didaftarkan ke FastAPI
from app.routes import auth as r_auth, user as r_user, post as r_post, interaction as r_interaction, chat as r_chat, notification as r_notification

# 4. Otomatis membuat tabel-tabel berdasarkan model yang terdaftar
Base.metadata.create_all(bind=engine)

# 5. Fungsi Otomatis untuk Seed Data Kategori jika tabel masih kosong
def seed_initial_categories():
    db: Session = SessionLocal()
    try:
        # Cek apakah sudah ada data di tabel categories
        category_count = db.query(CategoryModel).count()
        if category_count == 0:
            print("🌱 Menjalankan seeder otomatis untuk kategori awal RuangSisa...")
            initial_categories = [
                CategoryModel(id=1, category_name="Fashion", icon_name="shirt"),
                CategoryModel(id=2, category_name="Elektronik", icon_name="phone_android"),
                CategoryModel(id=3, category_name="Furnitur", icon_name="chair"),
                CategoryModel(id=4, category_name="Buku", icon_name="menu_book"),
                CategoryModel(id=5, category_name="Lainnya", icon_name="more_horiz")
            ]
            db.add_all(initial_categories)
            db.commit()
            print("✅ Seeding kategori berhasil disuntikkan!")
    except Exception as e:
        print(f"⚠️ Gagal menjalankan seeding: {e}")
    finally:
        db.close()

# Jalankan seeder tepat setelah tabel dipastikan ada
seed_initial_categories()

# 6. Inisialisasi FastAPI
app = FastAPI(
    title="RuangSisa RESTful API",
    description="Web Service Pendukung Aplikasi C2C Eco-Social Media RuangSisa",
    version="1.0.0"
)

# =======================================================================
# 🟢 MANAGEMENT AUTOMATION FOLDER STATIC ASSETS (KUNCI ABSOLUT PATH)
# =======================================================================

# 🛡️ KUNCI PENGAMAN PATH: Pastikan mengarah ke root project utama murni!
BASE_DIR = Path(__file__).resolve().parent  # folder app/
ROOT_DIR = BASE_DIR.parent                  # folder root project (ruangsisa_backend/)

# Definisikan folder statis menggunakan path absolut Path objek
STATIC_DIR = ROOT_DIR / "static"
UPLOADS_DIR = STATIC_DIR / "uploads"   # Foto barang jualan kontributor
AVATARS_DIR = STATIC_DIR / "avatars"   # Foto profil user/avatar

# Membuat folder secara absolut murni di root project
STATIC_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
AVATARS_DIR.mkdir(parents=True, exist_ok=True)

# Debug path
print("=" * 60)
print("📂 [PATH DEBUG] Static Files Configuration:")
print(f"   BASE_DIR: {BASE_DIR}")
print(f"   ROOT_DIR: {ROOT_DIR}")
print(f"   STATIC_DIR: {STATIC_DIR}")
print(f"   UPLOADS_DIR: {UPLOADS_DIR}")
print(f"   AVATARS_DIR: {AVATARS_DIR}")
print("=" * 60)

# 🔥 FIX MUTLAK MOUNTING: Menggunakan path STRING ABSOLUT agar tidak melenceng ke sub-folder /app!
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="zombie_uploads")
app.mount("/static/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads_fallback")
app.mount("/static/avatars", StaticFiles(directory=str(AVATARS_DIR)), name="avatars")

print("📸 [BACKEND STATIC] Jalur lama /uploads dan jalur baru /static sukses dikunci absolut!")
print(f"📸 [BACKEND STATIC] Static files served from: {STATIC_DIR}")

# Konfigurasi CORS agar bisa diakses dari domain manapun (Flutter app kita)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DAFTARKAN MIDDLEWARE LOG AKTIVITAS SECARA MANDIRI Di SINI
app.add_middleware(ActivityLogMiddleware)

# 7. Daftarkan Routers menggunakan alias router yang baru
app.include_router(r_auth.router)
app.include_router(r_user.router)
app.include_router(r_post.router)
app.include_router(r_interaction.router)
app.include_router(r_chat.router)
app.include_router(r_notification.router)

@app.get("/", tags=["Default"])
def root():
    return {
        "status": "success", 
        "message": "Welcome to RuangSisa API Services",
        "static_path": str(STATIC_DIR),
        "uploads_path": str(UPLOADS_DIR)
    }