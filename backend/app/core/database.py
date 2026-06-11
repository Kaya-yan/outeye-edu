"""
数据库配置
"""

from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import ssl

from app.core.config import settings


# SQLAlchemy 2.0 基类
class Base(DeclarativeBase):
    pass


# 创建异步引擎（处理Neon数据库的SSL连接）
db_url = settings.DATABASE_URL
connect_args = {}

# 如果是Neon数据库，添加SSL配置
if "neon.tech" in db_url:
    ssl_context = ssl.create_default_context()
    connect_args["ssl"] = ssl_context
    # 移除URL中的sslmode参数（asyncpg通过connect_args处理SSL）
    db_url = db_url.split("?")[0]

async_engine = create_async_engine(
    db_url,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=connect_args,
)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    bind=async_engine,
)


async def get_async_db():
    """获取数据库会话（异步）"""
    async with AsyncSessionLocal() as session:
        yield session


# 兼容性别名
get_db = get_async_db
