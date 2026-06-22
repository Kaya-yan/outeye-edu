"""专家评审数据模型"""

from sqlalchemy import Column, String, Float, Text, DateTime, JSON
from sqlalchemy.sql import func
import uuid

from app.db.base_class import Base


class ExpertReview(Base):
    """专家评审记录"""
    __tablename__ = "expert_reviews"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String, index=True, nullable=False)       # 关联的教案ID
    reviewer_name = Column(String(100), nullable=False)         # 评审专家姓名
    reviewer_title = Column(String(100), default="")            # 职称
    reviewer_institution = Column(String(200), default="")      # 单位

    # 5个评审维度（1-5分）
    score_objective = Column(Float, default=0)       # 教学目标合理性
    score_activity = Column(Float, default=0)        # 活动设计质量
    score_theory = Column(Float, default=0)          # 理论依据充分性
    score_differentiation = Column(Float, default=0) # 差异化考虑
    score_practicability = Column(Float, default=0)  # 课堂可实施性
    score_total = Column(Float, default=0)           # 总平均分

    comments = Column(Text, default="")              # 评审意见
    suggestion = Column(Text, default="")            # 改进建议
    created_at = Column(DateTime(timezone=True), server_default=func.now())
