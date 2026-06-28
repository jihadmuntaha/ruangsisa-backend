import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Memastikan Python mengenali folder 'app' dari root directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.user import UserModel  
from app.models.post import CategoryModel

load_dotenv()

def run_seeder():
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        DATABASE_URL = "sqlite:///./ruangsisa.db"
        print("ℹ️ DATABASE_URL tidak ditemukan di .env, seeding ke SQLite lokal...")
    else:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        print("🚀 Menghubungkan ke Cloud Database untuk proses seeding...")

    if "sqlite" in DATABASE_URL:
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        print("⏳ Mengecek data kategori yang sudah ada...")
        existing_categories = db.query(CategoryModel).count()
        if existing_categories > 0:
            print("⚠️ Database sudah memiliki data kategori. Proses seeding dibatalkan agar tidak duplikat.")
            return

        print("🌱 Memulai proses inject data master kategori baru...")
        
        # Daftar kategori umum & universal untuk marketplace/donasi barang bekas
        data_kategori = [
            {"category_name": "Fashion", "icon_name": "checkroom"},
            {"category_name": "Sepatu & Alas Kaki", "icon_name": "shopping_bag"},
            {"category_name": "Perlengkapan Bayi", "icon_name": "child_care"},
            {"category_name": "Perabotan & Rumah Tangga", "icon_name": "chair"},
            {"category_name": "Aksesoris & Lainnya", "icon_name": "category"}
        ]

        for item in data_kategori:
            new_category = CategoryModel(
                category_name=item["category_name"],
                icon_name=item["icon_name"]
            )
            db.add(new_category)
        
        db.commit()
        print(f"✅ SUCCESS! {len(data_kategori)} Data master kategori RuangSisa berhasil disuntikkan!")

    except Exception as e:
        db.rollback()
        print(f"❌ Terjadi error saat proses seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_seeder()