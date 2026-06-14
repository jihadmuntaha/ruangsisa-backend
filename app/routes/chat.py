from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List
from app.config.database import get_db
from app.models.interaction import ChatRoomModel, MessageModel
from app.schemas.chat import ChatRoomCreate, ChatRoomResponse, MessageCreate, MessageResponse
from app.middleware.auth_bearer import get_current_user
from app.models.user import User as UserModel

router = APIRouter(prefix="/api/chats", tags=["Direct Messages & Chat"])

# 🚪 1. Buka atau Buat Ruang Obrolan Baru (Anti-Duplikat Room)
@router.post("/room", response_model=ChatRoomResponse)
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
        return existing_room

    # Jika belum ada, rakit room baru
    new_room = ChatRoomModel(
        user_one_id=current_user.id,
        user_two_id=room_data.receiver_id,
        last_message="Memulai obrolan..."
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room


# 📜 2. Ambil Semua Daftar Chat Aktif Saya (Menu Chat List di Flutter)
@router.get("/rooms", response_model=List[ChatRoomResponse])
def get_my_chat_rooms(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    # Ambil room yang mana user_one ATAU user_two adalah SAYA, urutkan chat yang paling baru update
    rooms = db.query(ChatRoomModel).filter(
        or_(ChatRoomModel.user_one_id == current_user.id, ChatRoomModel.user_two_id == current_user.id)
    ).order_by(ChatRoomModel.updated_at.desc()).all()
    return rooms


# ✉️ 3. Kirim Pesan Teks Privat Baru
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

    # Ambil riwayat pesan, urutkan dari yang paling lama agar merayap logis ke bawah layar HP
    messages = db.query(MessageModel).filter(MessageModel.chat_id == chat_id).order_by(MessageModel.created_at.asc()).all()
    return messages