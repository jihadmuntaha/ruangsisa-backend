from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from app.config.database import Base

class NotificationModel(Base):
    __tablename__ = "notifications"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    type = Column(String, nullable=False)  
    reference_id = Column(String, nullable=True)  
    is_read = Column(Boolean, default=False)
    created_at = Column(
    DateTime(timezone=True), 
    default=lambda: datetime.datetime.now(datetime.timezone.utc)
)

    # 🟢 Menunjuk ke model User, dan back_populates mencocokkan properti di User
    user = relationship("User", back_populates="notifications")