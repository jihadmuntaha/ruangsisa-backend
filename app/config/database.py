import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 🟢 JEMBATAN BADAK + PAKSA UTF-8 ENCODING ANTI-EROR BINARY
DATABASE_URL = None
try:
    root_path = Path(__file__).resolve().parent.parent.parent
    env_file = root_path / ".env"
    
    if env_file.exists():
        # Tambahkan encoding="utf-8" dan errors="ignore" agar baris biner aneh dilewati otomatis
        with open(env_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip().startswith("DATABASE_URL"):
                    value = line.split("=", 1)[1].strip().strip('"').strip("'")
                    DATABASE_URL = value
                    break
except Exception as e:
    print(f"⚠️ Gagal membaca .env secara manual: {e}")

FORCE_LOCAL_SQLITE = False

if FORCE_LOCAL_SQLITE:
    DATABASE_URL = "sqlite:///./ruangsisa.db"
else:
    if not DATABASE_URL:
        DATABASE_URL = os.environ.get("DATABASE_URL")

# Fallback terakhir jika benar-benar zonk total
if not DATABASE_URL:
    print("⚠️ [DATABASE] Gagal total memuat URL Cloud. Menurunkan otomatis ke SQLite.")
    DATABASE_URL = "sqlite:///./ruangsisa.db"

# Otomatisasi pengganti skema postgres lama ke postgresql terbaru
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Konfigurasi engine berdasarkan database yang terpilih
if "sqlite" in DATABASE_URL:
    print("🖥️  [DATABASE] Menggunakan SQLite Lokal (ruangsisa.db)")
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    print("☁️  [DATABASE] Terkoneksi ke Cloud PostgreSQL Supabase")
    engine = create_engine(
        DATABASE_URL, 
        pool_size=5, 
        max_overflow=10, 
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