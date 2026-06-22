"""
用户反馈 API 端点
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid
from loguru import logger

from app.core.database import get_async_db
from app.models.learning import UserFeedback
from app.core.security import get_current_user
from app.utils.error_handler import handle_api_error

router = APIRouter()


# ============ 请求/响应模型 ============

class FeedbackCreate(BaseModel):
    """创建反馈请求"""
    feedback_type: str = Field(..., description="反馈类型：bug, feature, satisfaction, general")
    category: Optional[str] = Field(None, description="类别：analysis, lesson_plan, ui, performance")
    rating: Optional[int] = Field(None, description="评分（1-5）", ge=1, le=5)
    title: Optional[str] = Field(None, description="标题")
    content: Optional[str] = Field(None, description="内容")
    suggestion: Optional[str] = Field(None, description="建议")
    page_url: Optional[str] = Field(None, description="页面URL")
    browser_info: Optional[str] = Field(None, description="浏览器信息")


class FeedbackResponse(BaseModel):
    """反馈响应"""
    id: str
    feedback_type: str
    category: Optional[str]
    rating: Optional[int]
    title: Optional[str]
    content: Optional[str]
    suggestion: Optional[str]
    status: str
    admin_reply: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class FeedbackStats(BaseModel):
    """反馈统计"""
    total_count: int
    by_type: Dict[str, int]
    by_category: Dict[str, int]
    avg_rating: float
    pending_count: int


# ============ API端点 ============

@router.post("/", response_model=FeedbackResponse)
async def create_feedback(
    feedback: FeedbackCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """创建用户反馈"""
    try:
        new_feedback = UserFeedback(
            id=str(uuid.uuid4()),
            user_id=current_user["user_id"],
            feedback_type=feedback.feedback_type,
            category=feedback.category,
            rating=feedback.rating,
            title=feedback.title,
            content=feedback.content,
            suggestion=feedback.suggestion,
            page_url=feedback.page_url,
            browser_info=feedback.browser_info,
            status="pending",
            created_at=datetime.utcnow()
        )
        db.add(new_feedback)
        await db.commit()
        await db.refresh(new_feedback)

        logger.info(f"用户 {current_user['user_id']} 提交反馈: {feedback.feedback_type}")

        return FeedbackResponse(
            id=new_feedback.id,
            feedback_type=new_feedback.feedback_type,
            category=new_feedback.category,
            rating=new_feedback.rating,
            title=new_feedback.title,
            content=new_feedback.content,
            suggestion=new_feedback.suggestion,
            status=new_feedback.status,
            admin_reply=new_feedback.admin_reply,
            created_at=new_feedback.created_at.isoformat()
        )

    except Exception as e:
        raise handle_api_error(e, "创建反馈")


@router.get("/my", response_model=List[FeedbackResponse])
async def get_my_feedback(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """获取当前用户的反馈列表"""
    try:
        from sqlalchemy import select, desc

        result = await db.execute(
            select(UserFeedback)
            .where(UserFeedback.user_id == current_user["user_id"])
            .order_by(desc(UserFeedback.created_at))
            .offset(skip)
            .limit(limit)
        )
        feedbacks = result.scalars().all()

        return [
            FeedbackResponse(
                id=f.id,
                feedback_type=f.feedback_type,
                category=f.category,
                rating=f.rating,
                title=f.title,
                content=f.content,
                suggestion=f.suggestion,
                status=f.status,
                admin_reply=f.admin_reply,
                created_at=f.created_at.isoformat()
            )
            for f in feedbacks
        ]

    except Exception as e:
        raise handle_api_error(e, "获取反馈列表")


@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    db: AsyncSession = Depends(get_async_db)
):
    """获取反馈统计（管理员）"""
    try:
        from sqlalchemy import func, select

        # 总数
        result = await db.execute(select(func.count(UserFeedback.id)))
        total_count = result.scalar() or 0

        # 按类型统计
        result = await db.execute(
            select(UserFeedback.feedback_type, func.count(UserFeedback.id))
            .group_by(UserFeedback.feedback_type)
        )
        by_type = {row[0]: row[1] for row in result.all()}

        # 按类别统计
        result = await db.execute(
            select(UserFeedback.category, func.count(UserFeedback.id))
            .where(UserFeedback.category.isnot(None))
            .group_by(UserFeedback.category)
        )
        by_category = {row[0]: row[1] for row in result.all()}

        # 平均评分
        result = await db.execute(
            select(func.avg(UserFeedback.rating))
            .where(UserFeedback.rating.isnot(None))
        )
        avg_rating = result.scalar() or 0.0

        # 待处理数
        result = await db.execute(
            select(func.count(UserFeedback.id))
            .where(UserFeedback.status == "pending")
        )
        pending_count = result.scalar() or 0

        return FeedbackStats(
            total_count=total_count,
            by_type=by_type,
            by_category=by_category,
            avg_rating=round(avg_rating, 2),
            pending_count=pending_count
        )

    except Exception as e:
        raise handle_api_error(e, "获取反馈统计")


@router.post("/satisfaction")
async def submit_satisfaction_rating(
    rating: int = Query(..., ge=1, le=5, description="满意度评分（1-5）"),
    comment: Optional[str] = Query(None, description="评价"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """提交满意度评分"""
    try:
        feedback = UserFeedback(
            id=str(uuid.uuid4()),
            user_id=current_user["user_id"],
            feedback_type="satisfaction",
            rating=rating,
            content=comment,
            status="pending",
            created_at=datetime.utcnow()
        )
        db.add(feedback)
        await db.commit()

        return {"message": "感谢您的评价！", "rating": rating}

    except Exception as e:
        raise handle_api_error(e, "提交满意度评分")
