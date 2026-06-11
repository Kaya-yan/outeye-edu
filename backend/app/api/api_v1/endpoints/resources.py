"""
资源管理端点
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db

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


# 示例资源数据
SAMPLE_RESOURCES = [
    {
        "id": "1",
        "type": "theory",
        "title": "Krashen输入假说",
        "description": "Krashen的i+1输入假说是二语习得理论的核心，认为学习者需要接触略高于当前水平的输入",
        "category": "二语习得",
        "tags": ["krashen", "i+1", "acquisition"],
        "author": "Stephen Krashen",
        "quality_score": 0.95,
        "verified": True,
        "view_count": 150,
        "use_count": 45,
        "created_at": datetime.fromisoformat("2026-01-01T00:00:00")
    },
    {
        "id": "2",
        "type": "theory",
        "title": "Bloom认知分类学",
        "description": "认知层级从记忆到创造的六级分类，用于教学目标设计",
        "category": "教育心理学",
        "tags": ["bloom", "taxonomy", "cognition"],
        "author": "Benjamin Bloom",
        "quality_score": 0.95,
        "verified": True,
        "view_count": 120,
        "use_count": 38,
        "created_at": datetime.fromisoformat("2026-01-01T00:00:00")
    },
    {
        "id": "3",
        "type": "theory",
        "title": "CEFR框架",
        "description": "欧洲语言共同参考框架，A1-C2六级分类",
        "category": "语言评估",
        "tags": ["cefr", "assessment", "levels"],
        "author": "Council of Europe",
        "quality_score": 0.95,
        "verified": True,
        "view_count": 200,
        "use_count": 60,
        "created_at": datetime.fromisoformat("2026-01-01T00:00:00")
    },
    {
        "id": "4",
        "type": "case",
        "title": "环保主题课文教学案例",
        "description": "基于Krashen i+1理论的环保主题课文教学设计",
        "category": "教学案例",
        "tags": ["environment", "krashen", "lesson_plan"],
        "author": "张老师",
        "quality_score": 0.88,
        "verified": True,
        "view_count": 80,
        "use_count": 25,
        "created_at": datetime.fromisoformat("2026-02-15T00:00:00")
    },
    {
        "id": "5",
        "type": "template",
        "title": "课文分析报告模板",
        "description": "六维分析报告的标准模板",
        "category": "模板",
        "tags": ["template", "analysis", "report"],
        "author": "OutEye Team",
        "quality_score": 0.90,
        "verified": True,
        "view_count": 300,
        "use_count": 100,
        "created_at": datetime.fromisoformat("2026-03-01T00:00:00")
    }
]


@router.get("/", response_model=List[ResourceResponse])
async def get_resources(
    type: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取资源列表"""
    resources = SAMPLE_RESOURCES

    # 按类型过滤
    if type:
        resources = [r for r in resources if r["type"] == type]

    # 按分类过滤
    if category:
        resources = [r for r in resources if r["category"] == category]

    # 按标签过滤
    if tag:
        resources = [r for r in resources if tag in r["tags"]]

    return resources[skip:skip + limit]


@router.get("/theories/all")
async def get_all_theories(
    db: Session = Depends(get_db)
):
    """获取所有理论资源"""
    theories = [r for r in SAMPLE_RESOURCES if r["type"] == "theory"]
    return theories


@router.get("/cases/all")
async def get_all_cases(
    db: Session = Depends(get_db)
):
    """获取所有案例资源"""
    cases = [r for r in SAMPLE_RESOURCES if r["type"] == "case"]
    return cases


@router.get("/templates/all")
async def get_all_templates(
    db: Session = Depends(get_db)
):
    """获取所有模板资源"""
    templates = [r for r in SAMPLE_RESOURCES if r["type"] == "template"]
    return templates


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: str,
    db: Session = Depends(get_db)
):
    """获取单个资源"""
    for resource in SAMPLE_RESOURCES:
        if resource["id"] == resource_id:
            # 增加查看次数
            resource["view_count"] += 1
            return resource
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Resource not found"
    )


@router.post("/", response_model=ResourceResponse)
async def create_resource(
    resource: ResourceCreate,
    db: Session = Depends(get_db)
):
    """创建资源"""
    new_resource = {
        "id": str(len(SAMPLE_RESOURCES) + 1),
        "type": resource.type,
        "title": resource.title,
        "description": resource.description,
        "category": resource.category,
        "tags": resource.tags,
        "author": resource.author,
        "quality_score": 0.0,
        "verified": False,
        "view_count": 0,
        "use_count": 0,
        "created_at": datetime.now()
    }
    SAMPLE_RESOURCES.append(new_resource)
    return new_resource


@router.post("/search")
async def search_resources(
    query: str,
    type: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """搜索资源"""
    # 示例实现：简单关键词搜索
    results = []
    query_lower = query.lower()

    for resource in SAMPLE_RESOURCES:
        # 检查标题、描述、标签
        if (query_lower in resource["title"].lower() or
            query_lower in resource.get("description", "").lower() or
            any(query_lower in tag.lower() for tag in resource["tags"])):
            results.append(resource)

    # 按类型过滤
    if type:
        results = [r for r in results if r["type"] == type]

    # 按分类过滤
    if category:
        results = [r for r in results if r["category"] == category]

    return results