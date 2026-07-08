from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from app.config.database import Base
from app.utils import get_jakarta_time

class OTPModel(Base):
    __tablename__ = "password_otps"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(100), index=True, nullable=False)
    otp_code = Column(String(6), nullable=False)
    # Memastikan server default menggunakan WIB timestamp
    created_at = Column(TIMESTAMP(timezone=True), default=get_jakarta_time)