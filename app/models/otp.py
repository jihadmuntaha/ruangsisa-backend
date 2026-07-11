# app/models/otp.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime, timedelta
from app.config.database import Base
from app.utils import get_jakarta_time

class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    
    # 🟢 FIXED: Pastikan baris 'purpose' ini ada dan tidak typo, Beh!
    purpose = Column(String, default="register", nullable=False) 
    
    expired_at = Column(DateTime, nullable=False, default=lambda: get_jakarta_time() + timedelta(minutes=10))
    is_used = Column(Boolean, default=False, nullable=False)