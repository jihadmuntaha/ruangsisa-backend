import firebase_admin
from firebase_admin import credentials, messaging
from app.models.notification import NotificationModel
from sqlalchemy.orm import Session
import os

# 🟢 PERBAIKAN SAKLEK: Cari lokasi base directory proyek (ruangsisa_backend) secara presisi
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
cred_path = os.path.join(BASE_DIR, "serviceAccountKey.json")

print(f"🔍 [FCM CHECK] Mencari kunci privat Firebase di: {cred_path}")

if not firebase_admin._apps:
    # 🟢 1. Cek dulu apakah ada string rahasia JSON di Environment Variable Vercel
    firebase_env = os.environ.get("FIREBASE_CREDENTIALS")
    
    if firebase_env:
        try:
            print("🛡️ [FCM] Menginisialisasi Firebase via Environment Variable Cloud...")
            import json
            cred_dict = json.loads(firebase_env)
            
            # 🟢 FIX SAKTI: Bersihkan karakter garing (\n) bawaan private_key yang dirusak oleh parser Env Var Vercel
            if "private_key" in cred_dict:
                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("🛡️ [FCM SUCCESS] Firebase Admin SDK sukses terkoneksi di Cloud Vercel!")
        except Exception as cloud_err:
            print(f"🚨 [FCM CLOUD ERROR] Gagal inisialisasi dari Env Var: {cloud_err}")
    else:
        # 🟡 2. Jika tidak ada Env Var (berarti sedang lu run di laptop lokal), pakai file fisik
        if not os.path.exists(cred_path):
            print(f"🚨 [FCM CRITICAL] File '{cred_path}' TIDAK DITEMUKAN di lokal, BEH!")
        else:
            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("🛡️ [FCM SUCCESS] Firebase Admin SDK sukses terkoneksi murni di lokal!")
            except Exception as init_err:
                print(f"🚨 [FCM INIT ERROR] Gagal membaca isi json lokal: {init_err}")

def send_fcm_notification(target_token: str, title: str, body: str, data_payload: dict = None):
    if not target_token:
        print("⚠️ [FCM] Gagal kirim: Token device kosong, Beh!")
        return False

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data_payload or {},
            token=target_token,
        )
        response = messaging.send(message)
        print(f"🚀 [FCM SUCCESS] Notifikasi berhasil terkirim! ID: {response}")
        return True
    except Exception as e:
        print(f"🚨 [FCM ERROR] Gagal mengirim pesan via Firebase: {e}")
        return False
    
def save_and_send_notification(db: Session, user_id: int, title: str, body: str, notif_type: str, target_token: str = None, data_payload: dict = None):
    # 1. Simpan ke database lokal biar riwayatnya gak dummy
    try:
        new_notif = NotificationModel(
            user_id=user_id,
            title=title,
            body=body,
            type=notif_type
        )
        db.add(new_notif)
        db.commit()
        db.refresh(new_notif)
    except Exception as db_err:
        print(f"🚨 [DB NOTIF ERROR] Gagal menyimpan notif ke SQLite: {db_err}")

    # 2. Tembak FCM jika token tersedia murni
    if target_token:
        send_fcm_notification(target_token, title, body, data_payload)