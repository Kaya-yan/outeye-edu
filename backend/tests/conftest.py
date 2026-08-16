"""
测试共享配置
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import get_async_db, Base

# 使用内存 SQLite 进行测试（需要 aiosqlite）
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    """每个测试函数独立的内存数据库引擎，保证隔离"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(test_engine):
    """创建测试数据库会话"""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def client(test_db_session):
    """创建 TestClient，并注入测试数据库会话"""
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_async_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
