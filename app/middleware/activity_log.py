import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.config.database import SessionLocal
from app.models.activity_log import ActivityLog
import jwt
from app.middleware.auth_bearer import JWT_SECRET, ALGORITHM

class ActivityLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Biarkan request jalan dulu ke endpoint biar kita tahu status akhirnya (sukses/gagal)
        response = await call_next(request)
        
        # Kita hanya mencatat aksi perubahan data atau login/register (POST, PUT, DELETE)
        # Serta pastikan status responnya sukses (200/201) biar log yang masuk valid
        if request.method in ["POST", "PUT", "DELETE"] and response.status_code in [200, 201]:
            db: Session = SessionLocal()
            try:
                path = request.url.path
                action = f"{request.method} {path}"
                details = {}
                user_id = None

                # 2. DETEKSI USER DARI TOKEN JWT (Dengan Fallback Pengaman Ganda)
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    try:
                        token = auth_header.split(" ")[1]
                        # Taktik cerdas biar gak tabrakan sama token Google
                        try:
                            payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
                        except jwt.ExpiredSignatureError:
                            payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], options={"verify_exp": False})
                            
                        user_id = payload.get("user_id") or payload.get("sub")
                    except Exception:
                        pass

                # 3. PEMETAAN AKSI BIAR TEXT LOG-NYA CANTIK & RAPI
                if "/auth/login" in path:
                    action = "Login Aplikasi"
                    details = {"status": "Sukses Masuk"}
                elif "/auth/register" in path:
                    action = "Registrasi Akun Baru"
                    details = {"status": "Akun Berhasil Dibuat"}
                elif "/auth/register-face" in path or "premium" in path:
                    action = "Aktivasi Biometrik Face ID"
                    details = {"status": "Matriks Wajah Dikunci"}
                elif "/posts" in path:
                    action = "Manajemen Kain Perca/Limbah"
                    details = {"method": request.method, "info": "Perubahan data post textile waste"}

                # 4. KUNCI DATA KE DATABASE SQLITE (MENYESUAIKAN STRUKTUR KOLOM ASLI)
                if user_id or "/auth/" in path:
                    log_entry = ActivityLog(
                        user_id=int(user_id) if user_id and str(user_id).isdigit() else user_id,
                        activity=action,                  # ◄ Kolom 'activity' asli DB
                        description=json.dumps(details),  # ◄ Kolom 'description' asli DB
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent")
                    )
                    db.add(log_entry)
                    db.commit()
                    print(f"📡 [LOG AUTOMATION] Berhasil mencatat aktivitas dengan ID User [{user_id}]: {action}")
                    
            except Exception as e:
                print(f"🚨 [LOG ERROR] Gagal mencatat log aktivitas: {e}")
            finally:
                db.close()

        return response