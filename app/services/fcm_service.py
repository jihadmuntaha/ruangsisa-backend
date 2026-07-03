import firebase_admin
from firebase_admin import credentials, messaging
import os

# Path ke file service account key di root folder lu (sesuai image_0a1834.png)
credential_path = os.path.join(os.getcwd(), "serviceAccountKey.json")

# Inisialisasi Firebase Admin SDK secara aman (Cegah inisialisasi ganda)
if not firebase_admin._apps:
    try:
        if os.path.exists(credential_path):
            cred = credentials.Certificate(credential_path)
            firebase_admin.initialize_app(cred)
            print("🛡️ [FCM SUCCESS] Firebase Admin SDK sukses terkoneksi murni di Service!")
        else:
            print(f"❌ [FCM ERROR] Kunci privat tidak ditemukan di: {credential_path}")
    except Exception as init_err:
        print(f"🚨 [FCM INIT ERROR] Gagal inisialisasi SDK: {init_err}")

def send_push_notification(db, user_id: int, target_token: str, title: str, body: str, data_payload: dict):
    """
    Fungsi dasar penembak push notification layang via Google FCM.
    Lengkap dengan objek notification (biar banner turun) dan objek data (buat GetX Flutter).
    """
    if not target_token or target_token.strip() == "":
        print(f"⚠️ [FCM SERVICE SKIP] User ID {user_id} gak punya token valid.")
        return False

    # 🟢 FONDASI UTAMA PAYLOAD: Gabungkan Notification + Data
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        data=data_payload,  # Harus bertipe Dict[str, str]
        token=target_token
    )

    try:
        # Tembak langsung ke server Google FCM
        response = messaging.send(message)
        print(f"🚀 [FCM SUCCESS] Banner meluncur ke User ID {user_id}! Server Response: {response}")
        return True
    except Exception as e:
        print(f"❌ [FCM SEND ERROR] Google FCM menolak token untuk User ID {user_id}: {e}")
        return False