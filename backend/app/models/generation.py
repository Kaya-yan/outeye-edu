"""
生成记录模型：每次 LLM 生成（教案/课件/文化解释）落一条，
随产物保存 self_check 自检结果，质量可追溯。
"""

from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4

from app.core.database import Base


class GenerationLog(Base):
    """LLM 生成记录（新表，由 Base.metadata.create_all 自动创建）"""
    __tablename__ = "generation_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    analysis_id = Column(String(36), nullable=True, index=True)  # 关联分析记录（可空）
    stage = Column(String(50), nullable=False)  # lesson_plan / courseware_html / courseware_ppt / courseware_word / culture / revise
    prompt_name = Column(String(100), nullable=False)  # 模板名（lesson_plan_v2）
    prompt_version = Column(String(20), nullable=False)  # v2
    model = Column(String(50), nullable=False)
    fallback = Column(String(10), default="no")  # yes = 模板降级生成
    generation_duration = Column(Float, default=0.0)
    self_check = Column(JSON, nullable=True)  # 模型自检 JSON（含 time_matches_duration 等）
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "analysis_id": self.analysis_id,
            "stage": self.stage,
            "prompt_name": self.prompt_name,
            "prompt_version": self.prompt_version,
            "model": self.model,
            "fallback": self.fallback,
            "generation_duration": self.generation_duration,
            "self_check": self.self_check,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
