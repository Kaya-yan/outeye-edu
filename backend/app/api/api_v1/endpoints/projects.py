"""
项目管理端点
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.core.database import get_async_db
from app.core.security import get_current_user
from app.models.analysis import AnalysisRecord

router = APIRouter()


# Pydantic模型
class ProjectCreate(BaseModel):
    title: str
    course_type: str
    student_level: str
    duration_minutes: int
    source_text: str
    source_type: str = "text"
    tags: List[str] = []


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    title: str
    course_type: str
    student_level: str
    duration_minutes: int
    source_text: str
    analysis_status: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    course_type: Optional[str] = None
    student_level: Optional[str] = None
    duration_minutes: Optional[int] = None
    source_text: Optional[str] = None
    tags: Optional[List[str]] = None


def _record_to_response(record: AnalysisRecord) -> dict:
    """将 AnalysisRecord 转换为 ProjectResponse 格式"""
    return {
        "id": record.id,
        "user_id": record.user_id,
        "title": record.text_title,
        "course_type": record.course_type or "general",
        "student_level": record.student_level,
        "duration_minutes": record.duration_minutes or 45,
        "source_text": record.text_content,
        "analysis_status": record.analysis_status or "pending",
        "status": record.analysis_status or "draft",
        "created_at": record.created_at,
        "updated_at": record.updated_at or record.created_at,
    }


@router.get("/", response_model=List[ProjectResponse])
async def get_projects(
    project_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """获取项目列表（仅返回当前用户的项目）"""
    query = select(AnalysisRecord)
    query = query.where(AnalysisRecord.user_id == current_user["user_id"])

    # 按状态过滤
    if project_status:
        query = query.where(AnalysisRecord.analysis_status == project_status)

    query = query.order_by(AnalysisRecord.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    return [_record_to_response(r) for r in records]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """获取单个项目"""
    result = await db.execute(
        select(AnalysisRecord).where(AnalysisRecord.id == project_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return _record_to_response(record)


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """创建项目"""
    new_record = AnalysisRecord(
        id=str(uuid.uuid4()),
        user_id=current_user["user_id"],
        text_title=project.title,
        text_content=project.source_text,
        text_word_count=len(project.source_text.split()),
        student_level=project.student_level,
        course_type=project.course_type,
        duration_minutes=project.duration_minutes,
        analysis_status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(new_record)
    await db.commit()
    await db.refresh(new_record)
    return _record_to_response(new_record)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """更新项目"""
    result = await db.execute(
        select(AnalysisRecord).where(AnalysisRecord.id == project_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if project_update.title is not None:
        record.text_title = project_update.title
    if project_update.course_type is not None:
        record.course_type = project_update.course_type
    if project_update.student_level is not None:
        record.student_level = project_update.student_level
    if project_update.duration_minutes is not None:
        record.duration_minutes = project_update.duration_minutes
    if project_update.source_text is not None:
        record.text_content = project_update.source_text

    record.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(record)
    return _record_to_response(record)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """删除项目"""
    result = await db.execute(
        select(AnalysisRecord).where(AnalysisRecord.id == project_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    await db.delete(record)
    await db.commit()
    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/analyze")
async def analyze_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """分析项目（触发课文分析）"""
    result = await db.execute(
        select(AnalysisRecord).where(AnalysisRecord.id == project_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    record.analysis_status = "processing"
    record.updated_at = datetime.utcnow()
    await db.commit()

    return {
        "task_id": f"analysis_{project_id}",
        "status": "processing",
        "message": "Analysis started"
    }
