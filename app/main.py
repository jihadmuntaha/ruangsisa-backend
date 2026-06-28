from fastapi import FastAPI
from sqlalchemy.orm import Session
from app.config.database import engine, Base, SessionLocal, FORCE_LOCAL_SQLITE
from fastapi.middleware.cors import CORSMiddleware 
from app.middleware.activity_log import ActivityLogMiddleware
from fastapi.staticfiles import StaticFiles
import os

# 1. Import Models dengan alias (m_) atau secara spesifik agar tidak bentrok dengan routes
from app.models.post import CategoryModel
from app.models.user import User
from app.models.activity_log import ActivityLog
from app.models import interaction as m_interaction
from app.models import auth as m_auth

# 2. Import Routers untuk didaftarkan ke FastAPI (Sudah disapu bersih dari duplikasi)
from app.routes import auth as r_auth, user as r_user, post as r_post, interaction as r_interaction, chat as r_chat

# 3. Otomatis membuat tabel-tabel berdasarkan model yang terdaftar di database lokal (SQLite)
Base.metadata.create_all(bind=engine)

# 4. Fungsi Otomatis untuk Seed Data Kategori jika tabel masih kosong
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

# 5. Inisialisasi FastAPI
app = FastAPI(
    title="RuangSisa RESTful API",
    description="Web Service Pendukung Aplikasi C2C Eco-Social Media RuangSisa",
    version="1.0.0"
)

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 🔴 KUNCI PERBAIKAN: Pisahkan konfigurasi CORS dan ActivityLog secara mandiri!
# Konfigurasi CORS agar bisa diakses dari domain manapun (Flutter app kita)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Bisa diubah ke domain spesifik jika sudah deploy
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🟢 DAFTARKAN MIDDLEWARE LOG AKTIVITAS SECARA MANDIRI DI SINI, BEH!
app.add_middleware(ActivityLogMiddleware)


# 6. Daftarkan Routers menggunakan alias router yang baru
app.include_router(r_auth.router)
app.include_router(r_user.router)
app.include_router(r_post.router)
app.include_router(r_interaction.router)
app.include_router(r_chat.router)


@app.get("/", tags=["Default"])
def root():
    return {"status": "success", "message": "Welcome to RuangSisa API Services"}