from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks # 🟢 1. Inject BackgroundTasks di sini
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List
from app.config.database import get_db
from app.models.interaction import ChatRoomModel, MessageModel
from app.schemas.chat import ChatRoomCreate, ChatRoomResponse, MessageCreate, MessageResponse
from app.middleware.auth_bearer import get_current_user
from app.models.user import User as UserModel
from app.models.notification import NotificationModel
from firebase_admin import messaging

# Import service terpusat milik lu
from app.services.fcm_service import send_push_notification

router = APIRouter(prefix="/api/chats", tags=["Direct Messages & Chat"])

# 🚪 1. Buka atau Buat Ruang Obrolan Baru
@router.post("/room")
def get_or_create_chat_room(
    room_data: ChatRoomCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    if current_user.id == room_data.receiver_id:
        raise HTTPException(status_code=400, detail="Kamu tidak bisa chat dengan dirimu sendiri, Beh!")

    existing_room = db.query(ChatRoomModel).filter(
        or_(
            and_(ChatRoomModel.user_one_id == current_user.id, ChatRoomModel.user_two_id == room_data.receiver_id),
            and_(ChatRoomModel.user_one_id == room_data.receiver_id, ChatRoomModel.user_two_id == current_user.id)
        )
    ).first()

    if existing_room:
        room = existing_room
    else:
        new_room = ChatRoomModel(
            user_one_id=current_user.id,
            user_two_id=room_data.receiver_id,
            last_message="Memulai obrolan..."
        )
        db.add(new_room)
        db.commit()
        db.refresh(new_room)
        room = new_room

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

    unread_messages = db.query(MessageModel).filter(
        and_(
            MessageModel.chat_id == room.id,
            MessageModel.sender_id != current_user.id,
            MessageModel.is_read == False
        )
    ).count()

    return {
        "id": room.id,
        "user_one_id": room.user_one_id,
        "user_two_id": room.user_two_id,
        "last_message": room.last_message,
        "updated_at": room.updated_at,
        "is_read": room.is_read if hasattr(room, "is_read") else False,
        "receiver": receiver_data,
        "unread_count": unread_messages
    }


# 📜 2. Ambil Semua Daftar Chat Aktif Saya
@router.get("/rooms", response_model=List[ChatRoomResponse])
def get_my_chat_rooms(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    rooms = db.query(ChatRoomModel).filter(
        or_(ChatRoomModel.user_one_id == current_user.id, ChatRoomModel.user_two_id == current_user.id)
    ).order_by(ChatRoomModel.updated_at.desc()).all()
    
    room_list = []
    
    for room in rooms:
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
                "name": "Pengguna Keluar",
                "avatar": None
            }
        
        unread_messages = db.query(MessageModel).filter(
            and_(
                MessageModel.chat_id == room.id,
                MessageModel.sender_id != current_user.id,
                MessageModel.is_read == False
            )
        ).count()
        
        room_list.append({
            "id": room.id,
            "user_one_id": room.user_one_id,
            "user_two_id": room.user_two_id,
            "last_message": room.last_message,
            "updated_at": room.updated_at,
            "is_read": room.is_read if hasattr(room, "is_read") else False,
            "receiver": receiver_data,
            "unread_count": unread_messages
        })
        
    return room_list


# ✉️ 3. Kirim Pesan Teks Privat Baru + MELETUPKAN NOTIFIKASI FCM
def _process_fcm_delivery(receiver_token: str, title: str, body: str, payload: dict):
    # Fungsi background tasks murni untuk jabat tangan Firebase saja
    # JANGAN memanggil objek 'db' bawaan endpoint utama di dalam fungsi ini jika tidak diperlukan!
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=payload,
            token=receiver_token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    channel_id="ruangsisa_high_channel"
                )
            )
        )
        messaging.send(message)
        print("🚀 [FCM SUCCESS] Berhasil meletup di latar belakang cloud!")
    except Exception as fcm_err:
        print(f"🚨 [FCM ERROR]: {fcm_err}")


@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    msg_data: MessageCreate,
    background_tasks: BackgroundTasks, # 🟢 2. Inject BackgroundTasks ke parameter endpoint
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    room = db.query(ChatRoomModel).filter(ChatRoomModel.id == msg_data.chat_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room chat tidak ditemukan!")

    new_message = MessageModel(
        chat_id=msg_data.chat_id,
        sender_id=current_user.id,
        message_text=msg_data.message_text
    )
    db.add(new_message)
    room.last_message = msg_data.message_text
    
    db.commit()
    db.refresh(new_message)
    
    try:
        receiver_id = room.user_two_id if room.user_one_id == current_user.id else room.user_one_id
        receiver_user = db.query(UserModel).filter(UserModel.id == receiver_id).first()
        
        if receiver_user:
            # 1. Simpan riwayat ke DB lokal terlebih dahulu
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

            # 2. Tembak push notification menggunakan BackgroundTasks (Bypass Pembekuan Vercel)
            if receiver_user.fcm_token:
                payload_data = {
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                    "type": "chat",
                    "reference_id": str(current_user.id),
                    "avatar": current_user.avatar if current_user.avatar else ""
                }
                
                # 🚀 KUNCI SAKTI: Masukkan ke task latar belakang agar Vercel tidak membunuh proses di tengah jalan!
                background_tasks.add_task(
                    _process_fcm_delivery,
                    receiver_token=receiver_user.fcm_token,
                    title=f"📩 Pesan Baru dari {current_user.name}!",
                    body=msg_data.message_text if len(msg_data.message_text) <= 60 else f"{msg_data.message_text[:60]}...",
                    payload=payload_data
                )
            else:
                print(f"⚠️ [FCM SKIP] User {receiver_user.name} fcm_token kosong murni.")

    except Exception as e:
        print(f"🚨 [NOTIF GLOBAL ERROR] Alur notifikasi gagal total: {str(e)}")
        
    return new_message


# 💬 4. Tarik Riwayat Pesan di Dalam Room
@router.get("/rooms/{chat_id}/messages", response_model=List[MessageResponse])
def get_chat_history(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    room = db.query(ChatRoomModel).filter(ChatRoomModel.id == chat_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room chat tidak ditemukan!")
    
    if room.user_one_id != current_user.id and room.user_two_id != current_user.id:
        raise HTTPException(status_code=403, detail="Kamu tidak punya hak akses melihat chat ini, Beh!")

    db.query(MessageModel).filter(
        and_(
            MessageModel.chat_id == chat_id,
            MessageModel.sender_id != current_user.id,
            MessageModel.is_read == False
        )
    ).update({MessageModel.is_read: True}, synchronize_session=False)
    db.commit()

    messages = db.query(MessageModel).filter(MessageModel.chat_id == chat_id).order_by(MessageModel.created_at.asc()).all()
    
    return messages