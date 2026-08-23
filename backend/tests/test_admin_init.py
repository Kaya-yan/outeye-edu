"""
管理员初始化测试（TDD）

目标：
1. 确保 ADMIN_EMAIL 对应的用户存在且 is_admin=True
2. 确保唯一管理员（降级其他管理员）
"""

import pytest
from sqlalchemy import select

from app.models.user import User
from app.services.admin_init import initialize_admin


class TestInitializeAdmin:
    """管理员初始化逻辑测试"""

    @pytest.fixture
    def admin_email(self):
        return "Kaya-yan@outlook.com"

    @pytest.mark.asyncio
    async def test_creates_admin_if_not_exists(self, test_db_session, admin_email, monkeypatch):
        """管理员不存在时应创建"""
        monkeypatch.setattr("app.services.admin_init.ADMIN_EMAIL", admin_email)
        monkeypatch.setattr("app.services.admin_init.ADMIN_PASSWORD", "secure-password-123")

        result = await initialize_admin(test_db_session)

        assert result["created"] is True
        assert result["email"] == admin_email

        # 新逻辑统一以小写存储邮箱
        user = (await test_db_session.execute(
            select(User).where(User.email == admin_email.lower())
        )).scalar_one_or_none()
        assert user is not None
        assert user.is_admin is True
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_promotes_existing_user_to_admin(self, test_db_session, admin_email, monkeypatch):
        """已存在的普通用户应被提升为管理员"""
        monkeypatch.setattr("app.services.admin_init.ADMIN_EMAIL", admin_email)
        monkeypatch.setattr("app.services.admin_init.ADMIN_PASSWORD", "secure-password-123")

        existing = User(
            id="user-existing",
            email=admin_email,
            hashed_password="hashed",
            full_name="Kaya",
            is_active=True,
            is_admin=False,
        )
        test_db_session.add(existing)
        await test_db_session.commit()

        result = await initialize_admin(test_db_session)

        assert result["created"] is False

        user = (await test_db_session.execute(
            select(User).where(User.email == admin_email)
        )).scalar_one_or_none()
        assert user.is_admin is True

    @pytest.mark.asyncio
    async def test_demotes_other_admins(self, test_db_session, admin_email, monkeypatch):
        """应降级其他管理员，保证唯一管理员"""
        monkeypatch.setattr("app.services.admin_init.ADMIN_EMAIL", admin_email)
        monkeypatch.setattr("app.services.admin_init.ADMIN_PASSWORD", "secure-password-123")

        other_admin = User(
            id="other-admin",
            email="other-admin@example.com",
            hashed_password="hashed",
            full_name="Other Admin",
            is_active=True,
            is_admin=True,
        )
        test_db_session.add(other_admin)
        await test_db_session.commit()

        await initialize_admin(test_db_session)

        other = (await test_db_session.execute(
            select(User).where(User.email == "other-admin@example.com")
        )).scalar_one_or_none()
        assert other.is_admin is False

    @pytest.mark.asyncio
    async def test_admin_is_active(self, test_db_session, admin_email, monkeypatch):
        """管理员账户应始终为 active"""
        monkeypatch.setattr("app.services.admin_init.ADMIN_EMAIL", admin_email)
        monkeypatch.setattr("app.services.admin_init.ADMIN_PASSWORD", "secure-password-123")

        await initialize_admin(test_db_session)

        # 新逻辑统一以小写存储邮箱
        user = (await test_db_session.execute(
            select(User).where(User.email == admin_email.lower())
        )).scalar_one_or_none()
        assert user.is_active is True
