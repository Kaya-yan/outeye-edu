"""
项目管理端点
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db

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


# 示例项目数据
SAMPLE_PROJECTS = [
    {
        "id": "1",
        "user_id": "1",
        "title": "Environmental Protection Text Analysis",
        "course_type": "intensive_reading",
        "student_level": "B2",
        "duration_minutes": 90,
        "source_text": "Climate change is one of the most pressing issues facing our planet today...",
        "analysis_status": "completed",
        "status": "draft",
        "created_at": "2026-06-01T10:00:00",
        "updated_at": "2026-06-01T10:30:00"
    },
    {
        "id": "2",
        "user_id": "1",
        "title": "Cross-cultural Communication Lesson",
        "course_type": "oral_english",
        "student_level": "B1",
        "duration_minutes": 45,
        "source_text": "In today's globalized world, understanding cultural differences is essential...",
        "analysis_status": "pending",
        "status": "draft",
        "created_at": "2026-06-02T14:00:00",
        "updated_at": "2026-06-02T14:00:00"
    }
]


@router.get("/", response_model=List[ProjectResponse])
async def get_projects(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取项目列表"""
    # 示例实现：返回示例数据
    projects = SAMPLE_PROJECTS

    # 按用户ID过滤
    if user_id:
        projects = [p for p in projects if p["user_id"] == user_id]

    # 按状态过滤
    if status:
        projects = [p for p in projects if p["status"] == status]

    return projects[skip:skip + limit]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """获取单个项目"""
    for project in SAMPLE_PROJECTS:
        if project["id"] == project_id:
            return project
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Project not found"
    )


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    user_id: str = "1",  # 示例：默认用户ID
    db: Session = Depends(get_db)
):
    """创建项目"""
    new_project = {
        "id": str(len(SAMPLE_PROJECTS) + 1),
        "user_id": user_id,
        "title": project.title,
        "course_type": project.course_type,
        "student_level": project.student_level,
        "duration_minutes": project.duration_minutes,
        "source_text": project.source_text,
        "analysis_status": "pending",
        "status": "draft",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    SAMPLE_PROJECTS.append(new_project)
    return new_project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """更新项目"""
    for project in SAMPLE_PROJECTS:
        if project["id"] == project_id:
            if project_update.title:
                project["title"] = project_update.title
            if project_update.course_type:
                project["course_type"] = project_update.course_type
            if project_update.student_level:
                project["student_level"] = project_update.student_level
            if project_update.duration_minutes:
                project["duration_minutes"] = project_update.duration_minutes
            if project_update.source_text:
                project["source_text"] = project_update.source_text
            if project_update.tags:
                project["tags"] = project_update.tags
            project["updated_at"] = datetime.now().isoformat()
            return project
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Project not found"
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """删除项目"""
    for i, project in enumerate(SAMPLE_PROJECTS):
        if project["id"] == project_id:
            del SAMPLE_PROJECTS[i]
            return {"message": "Project deleted successfully"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Project not found"
    )


@router.post("/{project_id}/analyze")
async def analyze_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """分析项目（触发课文分析）"""
    for project in SAMPLE_PROJECTS:
        if project["id"] == project_id:
            # 更新分析状态
            project["analysis_status"] = "processing"
            project["updated_at"] = datetime.now().isoformat()

            # 示例：返回分析任务ID
            return {
                "task_id": f"analysis_{project_id}",
                "status": "processing",
                "message": "Analysis started"
            }
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Project not found"
    )