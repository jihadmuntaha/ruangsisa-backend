from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.config.database import get_db
from app.models.post import PostModel, CategoryModel
from app.schemas.post import PostCreate, PostResponse, CategoryResponse
from app.middleware.auth_bearer import get_current_user
from app.models.user import UserModel

router = APIRouter(prefix="/api", tags=["Feeds & Posts"])

# 1. Ambil Semua Kategori untuk Filter Beranda Flutter
@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return db.query(CategoryModel).all()

# 2. Ambil Semua Postingan Barang (Feed Beranda)
# Sudah support filter optional berdasarkan kategori / pencarian kata kunci
@router.get("/posts", response_model=List[PostResponse])
def get_all_posts(
    category_id: Optional[int] = None, 
    search: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    query = db.query(PostModel)
    
    # Filter Kategori jika diklik di Flutter
    if category_id:
        query = query.filter(PostModel.category_id == category_id)
    
    # Filter Pencarian Bento-Grid Eksplor
    if search:
        query = query.filter(PostModel.title.contains(search))
        
    return query.order_by(PostModel.created_at.desc()).all()

# 3. Membuat Postingan Kontribusi Baru
# Catatan: Sementara user_id kita hardcode ke id=1 dulu, nanti setelah ini kita pasang middleware JWT
@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_data: PostCreate, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user) # <-- PASANG SATPAM JWT DI SINI
):
    # Validasi tipe post kondisional
    if post_data.post_type == "Dijual" and not post_data.price:
        raise HTTPException(status_code=400, detail="Tipe dijual wajib menyertakan harga!")
    if post_data.post_type == "Barter" and not post_data.barter_wishlist:
        raise HTTPException(status_code=400, detail="Tipe barter wajib menyertakan wishlist!")

    # SEKARANG DATA USER_ID DIBACA OTOMATIS DARI TOKEN ORANG YANG LOGIN
    new_post = PostModel(
        user_id=current_user.id, # <-- Tidak di-hardcode angka 1 lagi!
        category_id=post_data.category_id,
        title=post_data.title,
        description=post_data.description,
        post_type=post_data.post_type,
        price=post_data.price if post_data.post_type == "Dijual" else None,
        barter_wishlist=post_data.barter_wishlist if post_data.post_type == "Barter" else None
    )
    
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post