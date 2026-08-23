"""
PUT /users/me/password 端点测试

覆盖：
1. 旧密码正确 + 新密码合法 → 200，哈希更新
2. 旧密码错误 → 400
3. 新密码 < 8 位 → 400
4. 新旧密码相同 → 400
5. 未认证 → 401（路由依赖 get_current_user）
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_async_db
from app.core.security import get_current_user, get_password_hash
from app.models.user import User


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class FakeResult:
    def __init__(self, user):
        self._user = user

    def scalar_one_or_none(self):
        return self._user


class FakeSession:
    def __init__(self, user):
        self._user = user
        self.committed = False

    async def execute(self, _stmt):
        return FakeResult(self._user)

    async def commit(self):
        self.committed = True


def _make_user():
    return User(
        id="user-1",
        email="a@b.c",
        hashed_password=get_password_hash("oldpass123"),
        full_name="Tester",
        is_active=True,
    )


def _client_as(user_dict, session):
    async def override_auth():
        return user_dict

    async def override_db():
        return session

    app.dependency_overrides[get_current_user] = override_auth
    app.dependency_overrides[get_async_db] = override_db
    return TestClient(app)


class TestChangePassword:
    def test_success_updates_hash(self):
        user = _make_user()
        session = FakeSession(user)
        client = _client_as({"user_id": "user-1", "email": "a@b.c", "is_admin": False}, session)

        res = client.put(
            "/api/v1/users/me/password",
            json={"old_password": "oldpass123", "new_password": "newpass456"},
        )

        assert res.status_code == 200
        assert session.committed
        from app.core.security import verify_password
        assert verify_password("newpass456", user.hashed_password)
        assert not verify_password("oldpass123", user.hashed_password)

    def test_wrong_old_password_400(self):
        user = _make_user()
        session = FakeSession(user)
        client = _client_as({"user_id": "user-1", "email": "a@b.c", "is_admin": False}, session)

        res = client.put(
            "/api/v1/users/me/password",
            json={"old_password": "wrongpass", "new_password": "newpass456"},
        )

        assert res.status_code == 400
        assert not session.committed

    def test_short_new_password_400(self):
        user = _make_user()
        session = FakeSession(user)
        client = _client_as({"user_id": "user-1", "email": "a@b.c", "is_admin": False}, session)

        res = client.put(
            "/api/v1/users/me/password",
            json={"old_password": "oldpass123", "new_password": "short"},
        )

        assert res.status_code == 400
        assert not session.committed

    def test_same_password_400(self):
        user = _make_user()
        session = FakeSession(user)
        client = _client_as({"user_id": "user-1", "email": "a@b.c", "is_admin": False}, session)

        res = client.put(
            "/api/v1/users/me/password",
            json={"old_password": "oldpass123", "new_password": "oldpass123"},
        )

        assert res.status_code == 400
        assert not session.committed

    def test_unauthenticated_401(self):
        client = TestClient(app, raise_server_exceptions=False)
        res = client.put(
            "/api/v1/users/me/password",
            json={"old_password": "oldpass123", "new_password": "newpass456"},
        )
        # HTTPBearer 缺失 Authorization header 时返回 403，凭证无效时 401
        assert res.status_code in (401, 403)
