# cek_db.py (Versi Detektif Kolom)
from app.config.database import SessionLocal
import app.main 
from app.models.activity_log import ActivityLog

def deteksi_kolom_log():
    db = SessionLocal()
    try:
        # Ambil satu data log mentah murni dari SQLite
        log_mentah = db.query(ActivityLog).first()
        
        print("\n==================================================")
        # Mengintip dictionary internal bawaan SQLAlchemy untuk melihat nama kolom asli
        print("🕵️‍♂️ DAFTAR NAMA KOLOM ASLI TABEL LU DI DATABASE:")
        print("==================================================")
        
        kolom_asli = log_mentah.__dict__
        for kunci in kolom_asli.keys():
            if not kunci.startswith('_'): # Buat nyaring data sampah internal SQLAlchemy
                print(f" 🟢 Kolom Ketemu: {kunci} -> Isi data: {kolom_asli[kunci]}")
                
        print("==================================================")
        print("👉 Cek kolom mana yang mirip buat ngganti kata 'action'!")
        
    except Exception as e:
        print(f"❌ Gagal membaca struktur: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    deteksi_kolom_log()