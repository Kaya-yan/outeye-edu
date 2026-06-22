"""专家评审 API"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.core.database import get_async_db
from app.core.security import get_current_user

router = APIRouter()


class ExpertReviewCreate(BaseModel):
    """创建专家评审"""
    plan_id: str = Field(..., description="关联的教案ID或文本标题")
    reviewer_name: str = Field(..., min_length=1, max_length=100)
    reviewer_title: str = Field("", max_length=100)
    reviewer_institution: str = Field("", max_length=200)
    score_objective: float = Field(..., ge=1, le=5, description="教学目标合理性")
    score_activity: float = Field(..., ge=1, le=5, description="活动设计质量")
    score_theory: float = Field(..., ge=1, le=5, description="理论依据充分性")
    score_differentiation: float = Field(..., ge=1, le=5, description="差异化考虑")
    score_practicability: float = Field(..., ge=1, le=5, description="课堂可实施性")
    comments: str = Field("", max_length=2000)
    suggestion: str = Field("", max_length=2000)


class ExpertReviewStats(BaseModel):
    """评审统计数据"""
    total_reviews: int
    avg_total: float
    avg_objective: float
    avg_activity: float
    avg_theory: float
    avg_differentiation: float
    avg_practicability: float
    recent_reviews: List[Dict[str, Any]]


@router.post("/submit")
async def submit_review(
    request: ExpertReviewCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    """提交专家评审"""
    try:
        from app.models.expert_review import ExpertReview

        avg_score = (
            request.score_objective +
            request.score_activity +
            request.score_theory +
            request.score_differentiation +
            request.score_practicability
        ) / 5

        review = ExpertReview(
            plan_id=request.plan_id,
            reviewer_name=request.reviewer_name,
            reviewer_title=request.reviewer_title,
            reviewer_institution=request.reviewer_institution,
            score_objective=request.score_objective,
            score_activity=request.score_activity,
            score_theory=request.score_theory,
            score_differentiation=request.score_differentiation,
            score_practicability=request.score_practicability,
            score_total=round(avg_score, 2),
            comments=request.comments,
            suggestion=request.suggestion,
        )
        db.add(review)
        await db.commit()

        logger.info(f"专家评审提交: {request.reviewer_name}, 总分{avg_score:.2f}")
        return {"status": "ok", "review_id": review.id, "avg_score": round(avg_score, 2)}

    except Exception as e:
        logger.error(f"专家评审提交失败: {e}")
        raise HTTPException(status_code=500, detail="提交失败，请稍后重试")


@router.get("/stats")
async def get_review_stats(
    db: AsyncSession = Depends(get_async_db),
):
    """获取评审统计数据（公开接口，用于展示）"""
    try:
        from app.models.expert_review import ExpertReview

        # 总数和平均分
        result = await db.execute(
            select(
                func.count(ExpertReview.id),
                func.avg(ExpertReview.score_total),
                func.avg(ExpertReview.score_objective),
                func.avg(ExpertReview.score_activity),
                func.avg(ExpertReview.score_theory),
                func.avg(ExpertReview.score_differentiation),
                func.avg(ExpertReview.score_practicability),
            )
        )
        row = result.first()

        if not row or row[0] == 0:
            return {
                "total_reviews": 0,
                "avg_total": 0,
                "avg_objective": 0,
                "avg_activity": 0,
                "avg_theory": 0,
                "avg_differentiation": 0,
                "avg_practicability": 0,
                "recent_reviews": [],
            }

        # 最近5条评审
        recent = await db.execute(
            select(ExpertReview)
            .order_by(ExpertReview.created_at.desc())
            .limit(5)
        )
        recent_list = []
        for r in recent.scalars():
            recent_list.append({
                "reviewer_name": r.reviewer_name,
                "reviewer_title": r.reviewer_title,
                "score_total": r.score_total,
                "comments": (r.comments[:100] + "...") if r.comments and len(r.comments) > 100 else (r.comments or ""),
            })

        return {
            "total_reviews": row[0],
            "avg_total": round(float(row[1] or 0), 2),
            "avg_objective": round(float(row[2] or 0), 2),
            "avg_activity": round(float(row[3] or 0), 2),
            "avg_theory": round(float(row[4] or 0), 2),
            "avg_differentiation": round(float(row[5] or 0), 2),
            "avg_practicability": round(float(row[6] or 0), 2),
            "recent_reviews": recent_list,
        }

    except Exception as e:
        logger.error(f"获取评审统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取统计数据失败")


@router.get("/list")
async def list_reviews(
    plan_id: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    """获取评审列表"""
    try:
        from app.models.expert_review import ExpertReview

        query = select(ExpertReview).order_by(ExpertReview.created_at.desc())
        if plan_id:
            query = query.where(ExpertReview.plan_id == plan_id)
        query = query.limit(20)

        result = await db.execute(query)
        reviews = []
        for r in result.scalars():
            reviews.append({
                "id": r.id,
                "plan_id": r.plan_id,
                "reviewer_name": r.reviewer_name,
                "reviewer_title": r.reviewer_title,
                "reviewer_institution": r.reviewer_institution,
                "score_objective": r.score_objective,
                "score_activity": r.score_activity,
                "score_theory": r.score_theory,
                "score_differentiation": r.score_differentiation,
                "score_practicability": r.score_practicability,
                "score_total": r.score_total,
                "comments": r.comments,
                "suggestion": r.suggestion,
                "created_at": str(r.created_at) if r.created_at else "",
            })

        return {"reviews": reviews, "count": len(reviews)}

    except Exception as e:
        logger.error(f"获取评审列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取评审列表失败")
