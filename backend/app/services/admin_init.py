"""
管理员初始化服务

确保唯一管理员存在：ADMIN_EMAIL 对应用户 is_admin=True，且降级其他管理员。
"""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User

# 模块级常量，便于测试 monkeypatch
ADMIN_EMAIL = settings.ADMIN_EMAIL
ADMIN_PASSWORD = getattr(settings, "ADMIN_PASSWORD", None)


async def initialize_admin(db: AsyncSession) -> dict:
    """初始化唯一管理员"""
    if not ADMIN_EMAIL:
        logger.warning("ADMIN_EMAIL 未配置，跳过管理员初始化")
        return {"created": False, "email": None, "skipped": True}

    email_lower = ADMIN_EMAIL.lower()

    # 1. 查找管理员用户（大小写不敏感，兼容历史混合大小写数据）
    result = await db.execute(select(User).where(func.lower(User.email) == email_lower))
    admin_user = result.scalar_one_or_none()

    created = False
    if admin_user is None:
        if not ADMIN_PASSWORD:
            logger.error("ADMIN_EMAIL 已配置但 ADMIN_PASSWORD 未配置，无法创建管理员")
            return {"created": False, "email": email_lower, "error": "missing_password"}

        admin_user = User(
            id=str(uuid.uuid4()),
            email=email_lower,
            hashed_password=get_password_hash(ADMIN_PASSWORD),
            full_name="Administrator",
            is_active=True,
            is_admin=True,
        )
        db.add(admin_user)
        created = True
        logger.info(f"已创建管理员账户: {email_lower}")
    else:
        # 2. 确保管理员账户 active 且 is_admin
        admin_user.is_admin = True
        admin_user.is_active = True
        logger.info(f"已提升管理员账户: {email_lower}")

    # 3. 降级其他管理员（保证唯一管理员）
    await db.execute(
        update(User)
        .where(func.lower(User.email) != email_lower, User.is_admin == True)  # noqa: E712
        .values(is_admin=False)
    )

    await db.commit()

    return {
        "created": created,
        "email": ADMIN_EMAIL,
    }
