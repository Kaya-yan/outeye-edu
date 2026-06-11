"""
用户模型
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    institution = Column(String(200), nullable=True)
    title = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # 关系
    analysis_records = relationship("AnalysisRecord", back_populates="user")
    lesson_plans = relationship("LessonPlan", back_populates="user")
    learning_records = relationship("LearningRecord", back_populates="user")
    feedback = relationship("UserFeedback", back_populates="user")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "institution": self.institution,
            "title": self.title,
            "bio": self.bio,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }
