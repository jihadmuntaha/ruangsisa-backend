from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List
from app.config.database import get_db
from app.models.interaction import ChatRoomModel, MessageModel
from app.schemas.chat import ChatRoomCreate, ChatRoomResponse, MessageCreate, MessageResponse
from app.middleware.auth_bearer import get_current_user
from app.models.user import User as UserModel
from app.services.fcm_service import send_push_notification
from app.models.notification import NotificationModel
from firebase_admin import messaging

# 🟢 PERBAIKAN IMPORT SAKTI: Gunakan service terpusat agar riwayat otomatis masuk SQLite!
from app.services.fcm_service import send_push_notification

router = APIRouter(prefix="/api/chats", tags=["Direct Messages & Chat"])

# 🚪 1. Buka atau Buat Ruang Obrolan Baru (Anti-Duplikat Room & Steril dari Pydantic Error)
@router.post("/room") # 🟢 Hapus sementara response_model=ChatRoomResponse jika Pydantic lu masih strict
def get_or_create_chat_room(
    room_data: ChatRoomCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    if current_user.id == room_data.receiver_id:
        raise HTTPException(status_code=400, detail="Kamu tidak bisa chat dengan dirimu sendiri, Beh!")

    # Cek apakah room antar kedua user ini sudah pernah dibuat sebelumnya
    existing_room = db.query(ChatRoomModel).filter(
        or_(
            and_(ChatRoomModel.user_one_id == current_user.id, ChatRoomModel.user_two_id == room_data.receiver_id),
            and_(ChatRoomModel.user_one_id == room_data.receiver_id, ChatRoomModel.user_two_id == current_user.id)
        )
    ).first()

    if existing_room:
        room = existing_room
    else:
        # Jika belum ada, rakit room baru
        new_room = ChatRoomModel(
            user_one_id=current_user.id,
            user_two_id=room_data.receiver_id,
            last_message="Memulai obrolan..."
        )
        db.add(new_room)
        db.commit()
        db.refresh(new_room)
        room = new_room

    # 🟢 SUNTIK DATA LAWAN SECARA AMAN (DIKTIONER MURNI)
    receiver_id = room.user_two_id if room.user_one_id == current_user.id else room.user_one_id
    receiver_user = db.query(UserModel).filter(UserModel.id == receiver_id).first()

    if receiver_user:
        receiver_data = {
            "id": receiver_user.id,
            "name": receiver_user.name,
            "avatar": getattr(receiver_user, "avatar", None)
        }
    else:
        receiver_data = {
            "id": receiver_id,
            "name": "Kontributor RuangSisa",
            "avatar": None
        }

    # Hitung pesan belum dibaca khusus untuk room ini
    unread_messages = db.query(MessageModel).filter(
        and_(
            MessageModel.chat_id == room.id,
            MessageModel.sender_id != current_user.id,
            MessageModel.is_read == False
        )
    ).count()

    # 🟢 RETURN STRUKTUR DICTIONARY MANUAL BIAR FASTAPI GAK BINGUNG SERIALIZE
    return {
        "id": room.id,
        "user_one_id": room.user_one_id,
        "user_two_id": room.user_two_id,
        "last_message": room.last_message,
        "updated_at": room.updated_at,
        "is_read": room.is_read if hasattr(room, "is_read") else False,
        "receiver": receiver_data, # Sudah steril murni berupa Dict!
        "unread_count": unread_messages
    }


# 📜 2. Ambil Semua Daftar Chat Aktif Saya (Menu Chat List di Flutter)
@router.get("/rooms", response_model=List[ChatRoomResponse])
def get_my_chat_rooms(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    rooms = db.query(ChatRoomModel).filter(
        or_(ChatRoomModel.user_one_id == current_user.id, ChatRoomModel.user_two_id == current_user.id)
    ).order_by(ChatRoomModel.updated_at.desc()).all()
    
    room_list = [] # 🟢 KITA PAKAI LIST BARU BIAR AMAN DARI STRUKTUR ORM ASLI
    
    for room in rooms:
        receiver_id = room.user_two_id if room.user_one_id == current_user.id else room.user_one_id
        receiver_user = db.query(UserModel).filter(UserModel.id == receiver_id).first()
        
        # 🟢 MAPPING OBJECT RECEIVER JADI DICTIONARY BIASA AGAR PYDANTIC GAK BINGUNG
        if receiver_user:
            receiver_data = {
                "id": receiver_user.id,
                "name": receiver_user.name,
                "avatar": getattr(receiver_user, "avatar", None) # Ambil avatar jika ada
            }
        else:
            receiver_data = {
                "id": receiver_id,
                "name": "Pengguna Keluar",
                "avatar": None
            }
        
        # Hitung pesan belum dibaca
        unread_messages = db.query(MessageModel).filter(
            and_(
                MessageModel.chat_id == room.id,
                MessageModel.sender_id != current_user.id,
                MessageModel.is_read == False
            )
        ).count()
        
        # 🟢 BENTUK STRUKTUR DICT YANG DIINGINKAN CHATROOMRESPONSE DENGAN KLOP
        room_list.append({
            "id": room.id,
            "user_one_id": room.user_one_id,
            "user_two_id": room.user_two_id,
            "last_message": room.last_message,
            "updated_at": room.updated_at,
            "is_read": room.is_read if hasattr(room, "is_read") else False,
            "receiver": receiver_data, # Sudah berupa dict murni, lolos sensor Pydantic!
            "unread_count": unread_messages
        })
        
    return room_list # Kembalikan list dict murni


# ✉️ 3. Kirim Pesan Teks Privat Baru + MELETUPKAN NOTIFIKASI FCM
@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    msg_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    # Pastikan room-nya beneran valid
    room = db.query(ChatRoomModel).filter(ChatRoomModel.id == msg_data.chat_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room chat tidak ditemukan!")

    # Simpan pesan baru ke tabel messages
    new_message = MessageModel(
        chat_id=msg_data.chat_id,
        sender_id=current_user.id,
        message_text=msg_data.message_text
    )
    db.add(new_message)

    # 🔄 Update kolom last_message di tabel chats agar Chat List di Flutter ikut ter-update otomatis
    room.last_message = msg_data.message_text
    
    db.commit()
    db.refresh(new_message)
    
    # 🟢 ================= INTEGRASI STRUKTUR NOTIFIKASI DASAR (REAL-TIME FIX) =================
    try:
        # 1. Tentukan siapa penerima pesan chat ini
        receiver_id = room.user_two_id if room.user_one_id == current_user.id else room.user_one_id
        receiver_user = db.query(UserModel).filter(UserModel.id == receiver_id).first()
        
        if receiver_user:
            # 2. SIMPAN RIWAYAT NOTIFIKASI KE DATABASE
            new_notif_log = NotificationModel(
                user_id=receiver_id,
                title=f"📩 Pesan Baru dari {current_user.name}!",
                body=msg_data.message_text if len(msg_data.message_text) <= 60 else f"{msg_data.message_text[:60]}...",
                type="chat",
                reference_id=str(msg_data.chat_id),
                is_read=False
            )
            db.add(new_notif_log)
            db.commit()
            print(f"💾 [DB SUCCESS] Riwayat notifikasi sukses dicatat untuk UserModel ID {receiver_id}!")

            # 🔥 3. TEMBAK PUSH NOTIFICATION KE FIREBASE GOOGLE (MELETUP REALTIME!)
            if receiver_user.fcm_token:
                try:
                    # Ambil token dari instance objek receiver_user murni
                    token_tujuan = receiver_user.fcm_token 
                    
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=f"📩 Pesan Baru dari {current_user.name}!",
                            body=msg_data.message_text if len(msg_data.message_text) <= 60 else f"{msg_data.message_text[:60]}...",
                        ),
                        data={
                            "click_action": "FLUTTER_NOTIFICATION_CLICK",
                            "chat_id": str(msg_data.chat_id),
                            "type": "chat"
                        },
                        token=token_tujuan,
                    )
                    
                    # Kirim paket sinyal ke server Google Firebase
                    response_fcm = messaging.send(message)
                    print(f"🚀 [FCM SUCCESS] Notifikasi berhasil meletup! ID: {response_fcm}")
                except Exception as fcm_err:
                    print(f"🚨 [FCM CORE ERROR] Gagal mengirim via Firebase SDK: {str(fcm_err)}")
            else:
                print(f"⚠️ [FCM SKIP] User {receiver_user.name} belum login di HP / fcm_token kosong murni.")

    except Exception as e:
        # 🟢 BERHASIL MENGUNCI EXCEPT UTAMA UTK BLOK TRY NOTIFIKASI
        print(f"🚨 [NOTIF GLOBAL ERROR] Alur notifikasi gagal total: {str(e)}")
        
    return new_message


# 💬 4. Tarik Riwayat Pesan di Dalam Room (Buka Room Chat di Flutter)
@router.get("/rooms/{chat_id}/messages", response_model=List[MessageResponse])
def get_chat_history(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    # Pastikan yang narik data emang salah satu pemilik room chat-nya (Aspek Privasi)
    room = db.query(ChatRoomModel).filter(ChatRoomModel.id == chat_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room chat tidak ditemukan!")
    
    if room.user_one_id != current_user.id and room.user_two_id != current_user.id:
        raise HTTPException(status_code=403, detail="Kamu tidak punya hak akses melihat chat ini, Beh!")

    # 🟢 SUNTIKKAN DI SINI, BEH! (Sebelum narik daftar messages ke UI Flutter)
    db.query(MessageModel).filter(
        and_(
            MessageModel.chat_id == chat_id,
            MessageModel.sender_id != current_user.id, # Pesan dari lawan bicara
            MessageModel.is_read == False              # Yang statusnya masih belum dibaca
        )
    ).update({MessageModel.is_read: True}, synchronize_session=False)
    db.commit()

    # Ambil riwayat pesan, urutkan dari yang paling lama agar merayap logis ke bawah layar HP
    messages = db.query(MessageModel).filter(MessageModel.chat_id == chat_id).order_by(MessageModel.created_at.asc()).all()
    
    return messages