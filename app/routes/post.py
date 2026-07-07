from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, File, UploadFile
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from app.config.database import get_db
from app.models.post import PostModel, CategoryModel
from app.models.user import User
import os
from datetime import datetime

router = APIRouter(prefix="/api", tags=["Posts"])

# ✅ GET ALL POSTS - Bersih total dari jalur /uploads/ lama
@router.get("/posts")
def get_all_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None, description="Cari nama barang spesifik"),
    post_type: Optional[str] = Query(None, description="Filter berdasarkan tipe post: Dijual atau Barter"),
    min_price: Optional[int] = Query(None, description="Filter harga minimum (hanya untuk tipe Dijual)"),
    max_price: Optional[int] = Query(None, description="Filter harga maksimum (hanya untuk tipe Dijual)"),
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Mendapatkan semua postingan dengan filter kategori dan pencarian teks spesifik
    """
    print("📡 [GET /api/posts] Request received dengan Filter Lanjutan")
    
    query = db.query(PostModel).options(joinedload(PostModel.author))
    
    # 1. 🟢 SELEKSI LIVE SEARCH: Saring judul barang jika parameter 'search' dikirim dari Flutter
    if search and search.strip() != "":
        search_text = f"%{search.strip()}%"
        query = query.filter(PostModel.title.like(search_text))

    # 2. SELEKSI KATEGORI: Tetap berjalan berdampingan dengan aman
    if category_id:
        query = query.filter(PostModel.category_id == category_id)

    # 3. SELEKSI TIPE POST: Dijual atau Barter
    if post_type and post_type in ["Dijual", "Barter", "Donasi"]:
        query = query.filter(PostModel.post_type == post_type)

    # 4. SELEKSI HARGA: Hanya berlaku untuk tipe Dijual
    if post_type == "Dijual":
        if min_price is not None:
            query = query.filter(PostModel.price >= min_price)
        if max_price is not None:
            query = query.filter(PostModel.price <= max_price)
    
    posts = query.order_by(PostModel.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for post in posts:
        author_name = "User RuangSisa"
        author_avatar = None
        
        if post.author:
            author_name = post.author.name
            author_avatar = post.author.avatar
        
        # 🟢 AUTO-FIX JALUR: Potong & ubah otomatis jika DB masih menyimpan string lama
        display_image = post.images
        if display_image and display_image.startswith("/uploads/"):
            display_image = display_image.replace("/uploads/", "/static/uploads/")
        
        result.append({
            "id": post.id,
            "user_id": post.user_id,
            "category_id": post.category_id,
            "title": post.title,
            "description": post.description,
            "images": display_image,  # Menggunakan jalur /static/
            "post_type": post.post_type,
            "price": post.price,
            "barter_wishlist": post.barter_wishlist,
            "status": post.status,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "author": {
                "id": post.user_id,
                "name": author_name,
                "avatar": author_avatar
            }
        })
    
    print(f"✅ Returning {len(result)} posts")
    return result

# ✅ GET SINGLE POST - Diproteksi juga agar tidak memuntahkan 404
@router.get("/posts/{post_id}")
def get_post_by_id(
    post_id: int,
    db: Session = Depends(get_db)
):
    post = db.query(PostModel).options(joinedload(PostModel.author)).filter(PostModel.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # 🟢 AUTO-FIX JALUR: Proteksi link single post agar Flutter tidak dapet /uploads/
    display_image = post.images
    if display_image and display_image.startswith("/uploads/"):
        display_image = display_image.replace("/uploads/", "/static/uploads/")
    
    return {
        "id": post.id,
        "user_id": post.user_id,
        "category_id": post.category_id,
        "title": post.title,
        "description": post.description,
        "images": display_image,  # Menggunakan jalur /static/
        "post_type": post.post_type,
        "price": post.price,
        "barter_wishlist": post.barter_wishlist,
        "status": post.status,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "author": {
            "id": post.user_id,
            "name": post.author.name if post.author else "User RuangSisa",
            "avatar": post.author.avatar if post.author else None
        }
    }


# ✅ GET CATEGORIES
@router.get("/categories")
def get_all_categories(db: Session = Depends(get_db)):
    categories = db.query(CategoryModel).all()
    return [
        {
            "id": cat.id,
            "category_name": cat.category_name,
            "icon_name": cat.icon_name
        }
        for cat in categories
    ]

# ✅ CREATE POST (CLEAN CLOUD STORAGE INTEGRATION)
@router.post("/posts", status_code=status.HTTP_201_CREATED)
async def create_post(
    title: str = Form(...),
    description: str = Form(...),
    user_id: int = Form(...),
    post_type: str = Form(...),
    category_id: int = Form(...),
    price: Optional[int] = Form(None),
    barter_wishlist: Optional[str] = Form(None),
    image_url: str = Form(...),  # 🟢 URL asli kiriman dari Supabase Storage via Flutter
    db: Session = Depends(get_db),
):
    try:
        print("=" * 50)
        print(f"📝 Creating post (Cloud Storage Mode):")
        print(f"   - title: {title}")
        print(f"   - user_id: {user_id}")
        print(f"   - post_type: {post_type}")
        print(f"   - category_id: {category_id}")
        print(f"   - image_url: {image_url}")
        print("=" * 50)
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail=f"Category {category_id} not found")
        
        # 🟢 BYPASS SAKTI TOTAL: Kita langsung pakai URL Supabase yang dibawa oleh image_url
        # Dua baris logika pembentuk safe_filename lama sudah dihapus karena bikin eror undefined
        db_image_url = image_url
        
        new_post = PostModel(
            user_id=user_id,
            category_id=category_id,
            title=title,
            description=description,
            images=db_image_url, # Menyimpan link online valid dari Supabase Storage
            post_type=post_type,
            price=price if post_type == "Dijual" else None,
            barter_wishlist=barter_wishlist if post_type == "Barter" else None,
        )
        
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        
        print(f"✅ Post created successfully! ID: {new_post.id}")
        
        return {
            "id": new_post.id,
            "user_id": new_post.user_id,
            "category_id": new_post.category_id,
            "title": new_post.title,
            "description": new_post.description,
            "images": new_post.images,
            "post_type": new_post.post_type,
            "price": new_post.price,
            "barter_wishlist": new_post.barter_wishlist,
            "status": new_post.status,
            "created_at": new_post.created_at.isoformat() if new_post.created_at else None,
            "author": {
                "id": user.id,
                "name": user.name,
                "avatar": user.avatar
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))