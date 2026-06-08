import sqlite3

# Konek ke file database lokal RuangSisa
conn = sqlite3.connect("ruangsisa.db")
cursor = conn.cursor()

try:
    cursor.execute("SELECT id, name, email FROM users")
    users = cursor.fetchall()
    
    print("\n=== DAFTAR AKUN RUANGSISA KAMU ===")
    for user in users:
        print(f"ID: {user[0]} | Nama: {user[1]} | Email: {user[2]}")
    print("===================================\n")
except Exception as e:
    print("Tabel users belum ada atau kosong:", e)

conn.close()