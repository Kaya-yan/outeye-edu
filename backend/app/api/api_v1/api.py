"""
API路由汇总
"""

from fastapi import APIRouter, Depends
from app.core.rate_limit import check_rate_limit

from app.api.api_v1.endpoints import (
    users,
    projects,
    resources,
    knowledge,
    health,
    wiki,
    rag,
    analysis_v2,
    analysis_whitebox,
    analysis_parse,
    feedback,
    expert_review,
)

# 创建API路由器
api_router = APIRouter()

# 注册各模块路由（添加速率限制依赖）

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["健康检查"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["用户管理"],
    dependencies=[Depends(check_rate_limit)]
)

api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["项目管理"],
    dependencies=[Depends(check_rate_limit)]
)

# 使用 analysis_v2 替代 analysis
api_router.include_router(
    analysis_v2.router,
    prefix="/analysis",
    tags=["智能分析"],
    dependencies=[Depends(check_rate_limit)]
)

api_router.include_router(
    resources.router,
    prefix="/resources",
    tags=["资源管理"],
    dependencies=[Depends(check_rate_limit)]
)

api_router.include_router(
    knowledge.router,
    prefix="/knowledge",
    tags=["知识库"],
    dependencies=[Depends(check_rate_limit)]
)

api_router.include_router(
    wiki.router,
    prefix="/wiki",
    tags=["Wiki知识库"],
    dependencies=[Depends(check_rate_limit)]
)

api_router.include_router(
    rag.router,
    prefix="/rag",
    tags=["RAG检索增强生成"],
    dependencies=[Depends(check_rate_limit)]
)

api_router.include_router(
    feedback.router,
    prefix="/feedback",
    tags=["用户反馈"],
    dependencies=[Depends(check_rate_limit)]
)

api_router.include_router(
    analysis_whitebox.router,
    prefix="/analysis",
    tags=["白盒分析"],
    dependencies=[Depends(check_rate_limit)]
)

api_router.include_router(
    analysis_parse.router,
    prefix="/analysis",
    tags=["文件解析"],
    dependencies=[Depends(check_rate_limit)]
)

api_router.include_router(
    expert_review.router,
    prefix="/expert-review",
    tags=["专家评审"],
)
