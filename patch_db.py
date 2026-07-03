import sqlite3
import os

# 1. Cari file database yang aktif di project lu
# Coba cek nama file database lu, kalau namanya 'ruangsisa.db' atau 'database.db' sesuaikan di bawah!
db_name = "ruangsisa.db" 

if os.path.exists(db_name):
    print(f"📦 Menghubungkan ke database aktif: {os.path.abspath(db_name)}")
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    try:
        # 2. Tambah kolom fcm_token secara paksa murni
        cursor.execute("ALTER TABLE users ADD COLUMN fcm_token TEXT;")
        conn.commit()
        print("✅ SUCCESS: Kolom 'fcm_token' berhasil disuntikkan langsung!")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
            print("💡 INFO: Kolom 'fcm_token' sebenarnya sudah ada di file ini.")
        else:
            print(f"🚨 EROR SQLITE: {e}")
    finally:
        conn.close()
else:
    print(f"❌ File {db_name} tidak ditemukan di folder ini! Coba cek nama file DB lu yang bener, Beh.")