"""
存储配额与磁盘监控

赛前数据治理：每用户 100MB 配额，磁盘用量可监控。
"""

import shutil
from typing import Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.document import Document

# 每用户配额：100MB
USER_QUOTA_BYTES = 100 * 1024 * 1024


async def get_user_storage_used(db: AsyncSession, user_id: str) -> int:
    """统计用户已使用的存储（字节）"""
    result = await db.execute(
        select(func.coalesce(func.sum(Document.file_size), 0)).where(
            Document.user_id == user_id
        )
    )
    return int(result.scalar() or 0)


async def check_user_quota(db: AsyncSession, user_id: str, new_size: int) -> bool:
    """检查用户是否还有配额上传 new_size 字节的内容"""
    used = await get_user_storage_used(db, user_id)
    return (used + new_size) <= USER_QUOTA_BYTES


def get_disk_usage(path: str) -> Dict[str, Any]:
    """获取磁盘用量统计（字节）"""
    usage = shutil.disk_usage(path)
    return {
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
    }
