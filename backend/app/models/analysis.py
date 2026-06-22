"""
分析记录模型
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class AnalysisRecord(Base):
    """课文分析记录"""
    __tablename__ = "analysis_records"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    text_title = Column(String(200), nullable=False)
    text_content = Column(Text, nullable=False)
    text_word_count = Column(Integer, default=0)
    student_level = Column(String(20), default="B1")

    # 项目管理字段
    course_type = Column(String(50), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    analysis_status = Column(String(20), default="pending")  # pending, processing, completed, failed

    # 分析结果
    lexical_result = Column(JSON, nullable=True)
    syntactic_result = Column(JSON, nullable=True)
    discourse_result = Column(JSON, nullable=True)
    cognitive_load_result = Column(JSON, nullable=True)

    # 综合评估
    overall_difficulty = Column(Float, default=0.0)
    cefr_level = Column(String(10), default="B1")
    teaching_suggestions = Column(JSON, nullable=True)

    # 白盒分析扩展字段
    enhancement_tags = Column(JSON, nullable=True)   # 增强标签列表
    learner_gap = Column(JSON, nullable=True)        # 学习者适配信息

    # 元数据
    analysis_duration = Column(Float, default=0.0)  # 分析耗时（秒）
    model_used = Column(String(50), default="rule-based")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="analysis_records")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "text_title": self.text_title,
            "text_content": self.text_content,
            "text_word_count": self.text_word_count,
            "student_level": self.student_level,
            "course_type": self.course_type,
            "duration_minutes": self.duration_minutes,
            "analysis_status": self.analysis_status,
            "overall_difficulty": self.overall_difficulty,
            "cefr_level": self.cefr_level,
            "analysis_duration": self.analysis_duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class LessonPlan(Base):
    """教案记录"""
    __tablename__ = "lesson_plans"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    analysis_id = Column(String(36), ForeignKey("analysis_records.id"), nullable=True)

    title = Column(String(200), nullable=False)
    student_level = Column(String(20), default="B1")
    duration = Column(Integer, default=45)  # 课时（分钟）

    # 教案内容
    objectives = Column(JSON, nullable=True)
    activities = Column(JSON, nullable=True)
    materials = Column(JSON, nullable=True)
    assessment = Column(JSON, nullable=True)
    differentiation = Column(JSON, nullable=True)
    homework = Column(Text, nullable=True)
    formatted_plan = Column(Text, nullable=True)

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="lesson_plans")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "student_level": self.student_level,
            "duration": self.duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
