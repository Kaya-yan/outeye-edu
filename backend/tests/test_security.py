"""
安全模块测试（TDD）

目标：
1. get_current_user 必须查询数据库并校验 is_active
2. get_current_user 必须返回 is_admin
3. 需提供 get_current_admin_user 依赖（仅管理员可用）
"""

import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_current_user,
    get_current_admin_user,
)
from app.models.user import User


class TestGetCurrentUser:
    """get_current_user 依赖测试"""

    @pytest.fixture
    def active_user(self):
        return User(
            id="user-123",
            email="test@example.com",
            hashed_password="hashed",
            full_name="Test User",
            is_active=True,
            is_admin=False,
        )

    @pytest.fixture
    def inactive_user(self):
        return User(
            id="user-456",
            email="inactive@example.com",
            hashed_password="hashed",
            full_name="Inactive User",
            is_active=False,
            is_admin=False,
        )

    @pytest.fixture
    def admin_user(self):
        return User(
            id="user-admin",
            email="admin@example.com",
            hashed_password="hashed",
            full_name="Admin User",
            is_active=True,
            is_admin=True,
        )

    @pytest.mark.asyncio
    async def test_returns_user_with_is_admin(self, test_db_session, active_user):
        """正常 Token 应返回包含 is_admin 的用户信息"""
        test_db_session.add(active_user)
        await test_db_session.commit()

        token = create_access_token(data={"sub": active_user.id, "email": active_user.email})
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        result = await get_current_user(credentials=creds, db=test_db_session)
        assert result["user_id"] == active_user.id
        assert result["email"] == active_user.email
        assert result["is_admin"] is False

    @pytest.mark.asyncio
    async def test_raises_401_for_inactive_user(self, test_db_session, inactive_user):
        """已禁用用户应返回 401"""
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials

        test_db_session.add(inactive_user)
        await test_db_session.commit()

        token = create_access_token(data={"sub": inactive_user.id, "email": inactive_user.email})
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds, db=test_db_session)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_for_nonexistent_user(self, test_db_session):
        """Token 对应用户不存在时应返回 401"""
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials

        token = create_access_token(data={"sub": "nonexistent", "email": "ghost@example.com"})
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds, db=test_db_session)
        assert exc_info.value.status_code == 401


class TestGetCurrentAdminUser:
    """get_current_admin_user 依赖测试"""

    @pytest.mark.asyncio
    async def test_allows_admin(self):
        """管理员用户应通过校验"""
        current_user = {"user_id": "admin-1", "email": "admin@example.com", "is_admin": True}

        result = await get_current_admin_user(current_user=current_user)
        assert result["user_id"] == "admin-1"
        assert result["is_admin"] is True

    @pytest.mark.asyncio
    async def test_rejects_non_admin(self):
        """非管理员用户应返回 403"""
        from fastapi import HTTPException

        current_user = {"user_id": "user-1", "email": "user@example.com", "is_admin": False}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(current_user=current_user)
        assert exc_info.value.status_code == 403
