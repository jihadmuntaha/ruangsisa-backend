import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Membaca URL database secara dinamis dari environment variable Vercel
DATABASE_URL = os.getenv("DATABASE_URL")

# Handle otomatis jika library mendeteksi format lama 'postgres://'
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback aman ke SQLite jika dijalankan lokal tanpa env agar tidak langsung crash
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./ruangsisa.db"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()