from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.config.database import Base
from app.utils import get_jakarta_time

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # Nullable jika tamu/guest
    activity = Column(String(100), nullable=False)  # Contoh: "Login Lokal", "Register Google", "Logout"
    description = Column(Text, nullable=True)  # Detail tambahan aktivitas
    ip_address = Column(String(45), nullable=True)  # Mencatat IP Address
    user_agent = Column(String(255), nullable=True)  # Mencatat info perangkat (Flutter/Web)
    created_at = Column(DateTime(timezone=True), default=get_jakarta_time)

    # Relasi balik ke model User
    user = relationship("User", back_populates="logs")