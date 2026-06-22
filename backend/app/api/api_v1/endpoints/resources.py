"""
资源管理端点
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.core.database import get_async_db
from app.core.security import get_current_user
from app.models.document import Document

router = APIRouter()


# Pydantic模型
class ResourceCreate(BaseModel):
    type: str
    title: str
    description: Optional[str] = None
    content: Optional[dict] = None
    category: Optional[str] = None
    tags: List[str] = []
    source: Optional[str] = None
    author: Optional[str] = None


class ResourceResponse(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str]
    category: Optional[str]
    tags: List[str]
    author: Optional[str]
    quality_score: float
    verified: bool
    view_count: int
    use_count: int
    created_at: datetime

    class Config:
        from_attributes = True


def _doc_to_response(doc: Document) -> dict:
    """将 Document 转换为 ResourceResponse 格式"""
    extra = doc.extra_data or {}
    return {
        "id": doc.id,
        "type": extra.get("resource_type", "document"),
        "title": doc.title,
        "description": extra.get("description"),
        "category": extra.get("category"),
        "tags": extra.get("tags", []),
        "author": extra.get("author"),
        "quality_score": extra.get("quality_score", 0.0),
        "verified": extra.get("verified", False),
        "view_count": extra.get("view_count", 0),
        "use_count": extra.get("use_count", 0),
        "created_at": doc.created_at,
    }


@router.get("/", response_model=List[ResourceResponse])
async def get_resources(
    type: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    """获取资源列表"""
    query = select(Document).offset(skip).limit(limit)
    result = await db.execute(query)
    docs = result.scalars().all()

    resources = [_doc_to_response(d) for d in docs]

    # 应用过滤（在Python层面，因为字段在JSON中）
    if type:
        resources = [r for r in resources if r["type"] == type]
    if category:
        resources = [r for r in resources if r["category"] == category]
    if tag:
        resources = [r for r in resources if tag in r["tags"]]

    return resources


@router.get("/theories/all")
async def get_all_theories(db: AsyncSession = Depends(get_async_db)):
    """获取所有理论资源"""
    result = await db.execute(select(Document))
    docs = result.scalars().all()
    resources = [_doc_to_response(d) for d in docs]
    return [r for r in resources if r["type"] == "theory"]


@router.get("/cases/all")
async def get_all_cases(db: AsyncSession = Depends(get_async_db)):
    """获取所有案例资源"""
    result = await db.execute(select(Document))
    docs = result.scalars().all()
    resources = [_doc_to_response(d) for d in docs]
    return [r for r in resources if r["type"] == "case"]


@router.get("/templates/all")
async def get_all_templates(db: AsyncSession = Depends(get_async_db)):
    """获取所有模板资源"""
    result = await db.execute(select(Document))
    docs = result.scalars().all()
    resources = [_doc_to_response(d) for d in docs]
    return [r for r in resources if r["type"] == "template"]


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """获取单个资源"""
    result = await db.execute(select(Document).where(Document.id == resource_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    # 增加查看次数
    extra = doc.extra_data or {}
    extra["view_count"] = extra.get("view_count", 0) + 1
    doc.extra_data = extra
    await db.commit()

    return _doc_to_response(doc)


@router.post("/", response_model=ResourceResponse)
async def create_resource(
    resource: ResourceCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """创建资源"""
    extra = {
        "resource_type": resource.type,
        "description": resource.description,
        "category": resource.category,
        "tags": resource.tags,
        "author": resource.author,
        "quality_score": 0.0,
        "verified": False,
        "view_count": 0,
        "use_count": 0,
    }
    if resource.content:
        extra["content"] = resource.content

    new_doc = Document(
        id=str(uuid.uuid4()),
        user_id=current_user["user_id"],
        title=resource.title,
        extra_data=extra,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    return _doc_to_response(new_doc)


@router.post("/search")
async def search_resources(
    query: str,
    type: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """搜索资源"""
    result = await db.execute(select(Document))
    docs = result.scalars().all()
    resources = [_doc_to_response(d) for d in docs]

    query_lower = query.lower()
    results = []
    for r in resources:
        if (query_lower in r["title"].lower() or
            query_lower in (r.get("description") or "").lower() or
            any(query_lower in tag.lower() for tag in r["tags"])):
            results.append(r)

    if type:
        results = [r for r in results if r["type"] == type]
    if category:
        results = [r for r in results if r["category"] == category]

    return results
