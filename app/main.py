from fastapi import FastAPI
from sqlalchemy.orm import Session
from app.config.database import engine, Base, SessionLocal
from app.models.post import CategoryModel
from app.models import interaction
from app.routes import auth, post, interaction, user

# 1. Otomatis membuat tabel-tabel berdasarkan model yang terdaftar
Base.metadata.create_all(bind=engine)

# 2. Fungsi Otomatis untuk Seed Data Kategori jika tabel masih kosong
def seed_initial_categories():
    db: Session = SessionLocal()
    try:
        # Cek apakah sudah ada data di tabel categories
        category_count = db.query(CategoryModel).count()
        if category_count == 0:
            print("🌱 Menjalankan seeder otomatis untuk kategori awal RuangSisa...")
            initial_categories = [
                CategoryModel(id=1, category_name="Pakaian", icon_name="shirt"),
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

# 3. Inisialisasi FastAPI
app = FastAPI(
    title="RuangSisa RESTful API",
    description="Web Service Pendukung Aplikasi C2C Eco-Social Media RuangSisa",
    version="1.0.0"
)

# 4. Daftarkan Routers
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(post.router)
app.include_router(interaction.router)

@app.get("/")
def root():
    return {"status": "success", "message": "Welcome to RuangSisa API Services"}