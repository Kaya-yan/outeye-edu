"""
A/B 评价收集

教师对 baseline/enhanced 两版的评价（选择、评分、评论）写入反馈表。
"""

import uuid
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.learning import UserFeedback


async def record_ab_evaluation(
    db: AsyncSession,
    user_id: str,
    chosen_version: str,
    rating: Optional[int] = None,
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    """记录教师对 A/B 两版的评价"""
    feedback = UserFeedback(
        id=str(uuid.uuid4()),
        user_id=user_id,
        feedback_type="ab_comparison",
        category="lesson_plan",
        rating=rating,
        title=chosen_version,  # "baseline" | "enhanced"
        content=comment,
        status="pending",
    )
    db.add(feedback)
    await db.commit()

    logger.info(f"A/B 评价已记录: user={user_id} chosen={chosen_version} rating={rating}")
    return {
        "feedback_id": feedback.id,
        "chosen_version": chosen_version,
        "rating": rating,
    }
