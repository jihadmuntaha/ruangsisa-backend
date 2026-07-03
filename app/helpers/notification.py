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
    if not os.path.exists(cred_path):
        print(f"🚨 [FCM CRITICAL] File '{cred_path}' TIDAK DITEMUKAN, BEH! Pastikan filenya sudah ditaruh di folder root backend.")
    else:
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("🛡️ [FCM SUCCESS] Firebase Admin SDK sukses terkoneksi murni!")
        except Exception as init_err:
            print(f"🚨 [FCM INIT ERROR] Gagal membaca isi json: {init_err}")

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