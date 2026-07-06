import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = None

# 1. Prioritas Utama: Ambil langsung dari Environment Variable Cloud Vercel
if os.environ.get("VERCEL"):
    DATABASE_URL = os.environ.get("DATABASE_URL")
    print("☁️ [DATABASE] Mengambil konfigurasi URL murni dari Vercel Cloud...")

# 2. Jika tidak berjalan di Vercel, gunakan pembacaan manual lokal (.env)
if not DATABASE_URL:
    try:
        root_path = Path(__file__).resolve().parent.parent.parent
        env_file = root_path / ".env"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.strip().startswith("DATABASE_URL"):
                        DATABASE_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    except Exception as e:
        print(f"⚠️ Gagal membaca .env secara manual: {e}")

# 3. Fallback jika semua jalur di atas zonk
if not DATABASE_URL:
    print("🖥️ [DATABASE] URL Cloud tidak ditemukan. Menurunkan otomatis ke SQLite Lokal.")
    DATABASE_URL = "sqlite:///./ruangsisa.db"

# Otomatisasi konversi skema postgres lama ke postgresql terbaru
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Konfigurasi engine berdasarkan jenis database
if "sqlite" in DATABASE_URL:
    print("🖥️ [DATABASE] Menggunakan SQLite Lokal (ruangsisa.db)")
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Cetak port yang digunakan untuk memastikan tidak meleset ke 5432 lagi
    print(f"☁️ [DATABASE] Menghubungkan ke Cloud PostgreSQL Supabase...")
    engine = create_engine(
        DATABASE_URL, 
        pool_size=3,          # Diperkecil agar ramah serverless
        max_overflow=0,       # Batasi overflow koneksi di Vercel
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Tambahkan ini di baris paling bawah file database.py lu, Beh!
FORCE_LOCAL_SQLITE = False