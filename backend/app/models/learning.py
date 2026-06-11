"""
学习记录和用户反馈模型
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class LearningRecord(Base):
    """学习记录"""
    __tablename__ = "learning_records"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 学习内容
    content_type = Column(String(50), nullable=False)  # analysis, lesson_plan, resource
    content_id = Column(String(36), nullable=True)
    content_title = Column(String(200), nullable=True)

    # 学习行为
    action = Column(String(50), nullable=False)  # view, complete, bookmark, share
    duration = Column(Integer, default=0)  # 学习时长（秒）

    # 学习效果
    score = Column(Float, nullable=True)  # 测试分数
    mastery_level = Column(String(20), nullable=True)  # 掌握程度

    # 元数据
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 关系
    user = relationship("User", back_populates="learning_records")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content_type": self.content_type,
            "content_id": self.content_id,
            "content_title": self.content_title,
            "action": self.action,
            "duration": self.duration,
            "score": self.score,
            "mastery_level": self.mastery_level,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class UserFeedback(Base):
    """用户反馈"""
    __tablename__ = "user_feedback"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 反馈内容
    feedback_type = Column(String(50), nullable=False)  # bug, feature, satisfaction, general
    category = Column(String(50), nullable=True)  # analysis, lesson_plan, ui, performance

    # 评分
    rating = Column(Integer, nullable=True)  # 1-5 分

    # 反馈详情
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)

    # 上下文信息
    page_url = Column(String(500), nullable=True)
    browser_info = Column(String(500), nullable=True)
    screenshot_url = Column(String(500), nullable=True)

    # 处理状态
    status = Column(String(20), default="pending")  # pending, reviewed, resolved
    admin_reply = Column(Text, nullable=True)

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="feedback")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "feedback_type": self.feedback_type,
            "category": self.category,
            "rating": self.rating,
            "title": self.title,
            "content": self.content,
            "suggestion": self.suggestion,
            "status": self.status,
            "admin_reply": self.admin_reply,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class UserBehavior(Base):
    """用户行为追踪"""
    __tablename__ = "user_behaviors"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(String(36), nullable=True, index=True)

    # 行为信息
    event_type = Column(String(50), nullable=False)  # page_view, click, api_call, error
    event_name = Column(String(100), nullable=False)
    page_url = Column(String(500), nullable=True)

    # 事件数据
    event_data = Column(JSON, nullable=True)

    # 性能指标
    duration = Column(Float, nullable=True)  # 耗时（毫秒）
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # 设备信息
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(50), nullable=True)
    device_type = Column(String(20), nullable=True)  # desktop, mobile, tablet

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "event_name": self.event_name,
            "page_url": self.page_url,
            "duration": self.duration,
            "success": self.success,
            "device_type": self.device_type,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
