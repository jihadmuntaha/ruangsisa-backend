from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.config.database import get_db
from app.models.post import PostModel, CategoryModel
from app.schemas.post import PostCreate, PostResponse # Pastikan di schemas sudah ada CategoryResponse jika dipakai
from app.middleware.auth_bearer import get_current_user
from app.models.user import User as UserModel

router = APIRouter(prefix="/api", tags=["Feeds & Posts"])

# 1. Ambil Semua Kategori untuk Filter Beranda Flutter
# Catatan: Jika schemas kamu memakai nama lain, sesuaikan response_model-nya
@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    return db.query(CategoryModel).all()


# 2. Ambil Semua Postingan Barang (Feed Beranda)
# Sudah support filter optional berdasarkan kategori / pencarian kata kunci otomatis
@router.get("/posts", response_model=List[PostResponse])
def get_all_posts(
    category_id: Optional[int] = None, 
    search: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    query = db.query(PostModel)
    
    # Filter Kategori jika diklik di Top Bar Flutter
    if category_id:
        query = query.filter(PostModel.category_id == category_id)
    
    # 🛠️ PERBAIKAN: Menggunakan ilike agar pencarian teks di Search Bar tidak case-sensitive
    if search:
        query = query.filter(PostModel.title.ilike(f"%{search}%"))
        
    return query.order_by(PostModel.created_at.desc()).all()


# 3. Membuat Postingan Kontribusi Baru (Fase Menu 3)
@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_data: PostCreate, 
    db: Session = Depends(get_db),
    # 🔴 BYPASS SEMENTARA: Kita komentari/matikan baris satpam JWT ini
    # current_user: UserModel = Depends(get_current_user) 
):
    # 🟢 BUAT MOCK USER: Hardcode objek user dummy sesuai ID lu di database (Misal ID: 4)
    # Ini biar sistem tetap mengira ada user valid yang sedang memposting barang
    from app.models.user import User as UserModel
    mock_user = db.query(UserModel).filter(UserModel.id == 1).first() # ◄ Sesuaikan angka 4 dengan ID user lu di SQLite
    
    if not mock_user:
        raise HTTPException(status_code=404, detail="User testing ID 4 belum dibuat di DB, Beh!")

    new_post = PostModel(
        user_id=mock_user.id, # ◄ Membaca otomatis dari mock user
        category_id=post_data.category_id,
        title=post_data.title,
        description=post_data.description,
        images=post_data.images,
        post_type=post_data.post_type,
        price=post_data.price,
        barter_wishlist=post_data.barter_wishlist
    )
    
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post