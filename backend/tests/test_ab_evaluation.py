"""
A/B 评价收集测试（TDD）

目标：教师对 baseline/enhanced 两版的评价被正确收集。
"""

import pytest
from sqlalchemy import select

from app.models.learning import UserFeedback
from app.services.analysis.ab_evaluation import record_ab_evaluation


class TestRecordABEvaluation:
    """A/B 评价收集测试"""

    @pytest.mark.asyncio
    async def test_records_evaluation(self, test_db_session):
        result = await record_ab_evaluation(
            test_db_session,
            user_id="user-1",
            chosen_version="enhanced",
            rating=5,
            comment="增强版证据更清晰",
        )

        assert result["feedback_id"] is not None

        stored = (await test_db_session.execute(
            select(UserFeedback).where(UserFeedback.user_id == "user-1")
        )).scalar_one_or_none()

        assert stored is not None
        assert stored.feedback_type == "ab_comparison"
        assert stored.title == "enhanced"
        assert stored.rating == 5
        assert stored.content == "增强版证据更清晰"
