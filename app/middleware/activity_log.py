import json
import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.config.database import SessionLocal


class ActivityLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Biarkan request utama meluncur bebas ke endpoint tujuan (Anti-Blocking Gerbang)
        response = await call_next(request)
        
        # Kita hanya mencatat aksi perubahan data atau login/register (POST, PUT, DELETE)
        if request.method in ["POST", "PUT", "DELETE"] and response.status_code in [200, 201]:
            db: Session = SessionLocal()
            try:
                # 🟢 SUNTIKKAN DI SINI (Local Import): Python baru membaca model ini 
                # TEPAT saat ada transaksi data, menghentikan eror circular import secara total!
                from app.models.activity_log import ActivityLog
                
                path = request.url.path
                action = f"{request.method} {path}"
                details = {}
                user_id = None

                # 2. DETEKSI USER DENGAN MODE SILENT (Ignore Signature & Expired)
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    try:
                        token = auth_header.split(" ")[1]
                        # Trik aman lu tetap terjaga sempurna:
                        payload = jwt.decode(
                            token, 
                            options={"verify_signature": False, "verify_exp": False}
                        )
                        user_id = payload.get("sub") or payload.get("user_id")
                    except Exception:
                        pass # Cuek jika token gagal dikupas

                # 3. PEMETAAN AKSI TEXT LOG RUANGSISA
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

                # 4. KUNCI DATA KE SUPABASE / POSTGRESQL LU
                if user_id or "/auth/" in path:
                    log_entry = ActivityLog(
                        user_id=int(user_id) if user_id and str(user_id).isdigit() else None,
                        activity=action,                                    
                        description=json.dumps(details),                                  
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent")
                        # Catatan: Kolom created_at otomatis terisi default(get_jakarta_time) dari model lu, Beh!
                    )
                    db.add(log_entry)
                    db.commit()
                    print(f"📡 [LOG AUTOMATION] Berhasil menyimpan audit log untuk User ID [{user_id}]: {action}")
                    
            except Exception as e:
                print(f"🚨 [LOG ERROR] Gagal mencatat log aktivitas: {e}")
            finally:
                db.close()

        return response