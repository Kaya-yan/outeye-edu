"""
健康检查端点
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db

router = APIRouter()


@router.get("")
async def health_check():
    """基础健康检查（含提示词模板部署诊断）"""
    prompts_status = {"available": [], "error": None}
    try:
        from app.services.prompt_manager import prompt_dir

        prompts_status["available"] = sorted(p.name for p in prompt_dir().glob("*.md"))
    except Exception as e:
        prompts_status["error"] = f"{type(e).__name__}: {e}"
    return {
        "status": "healthy",
        "service": "OutEye Edu API",
        "version": "1.0.0",
        "prompts": prompts_status,
    }


@router.get("/db")
async def db_health_check(db: Session = Depends(get_db)):
    """数据库健康检查"""
    try:
        # 执行简单查询测试数据库连接
        result = db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "result": result.scalar()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }