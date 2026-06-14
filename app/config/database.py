import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# PAKSA AMAN: Selama development lokal, kita bypass DATABASE_URL bawaan cloud
# Jika ingin balik ke online nanti, tinggal ubah parameter ini jadi False atau hapus baris ini
FORCE_LOCAL_SQLITE = True

if FORCE_LOCAL_SQLITE:
    DATABASE_URL = "sqlite:///./ruangsisa.db"
else:
    DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback standar jika variabel env kosong
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./ruangsisa.db"

# Otomatisasi pengganti skema postgres lama ke postgresql terbaru (Vercel/Render)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


# Konfigurasi engine berdasarkan database yang terpilih
if "sqlite" in DATABASE_URL:
    print("🖥️  [DATABASE] Menggunakan SQLite Lokal (ruangsisa.db)")
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    print("☁️  [DATABASE] Terkoneksi ke Cloud PostgreSQL")
    engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()