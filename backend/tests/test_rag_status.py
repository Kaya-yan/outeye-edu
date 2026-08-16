"""
RAG 系统状态测试（TDD）

目标：
1. embedding 模型已加载 → {"status":"ready"}
2. 未加载 → {"status":"loading"}
3. 需认证
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import get_current_user


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client():
    async def override_auth():
        return {"user_id": "user-1", "email": "a@b.c", "is_admin": False}

    app.dependency_overrides[get_current_user] = override_auth
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestRAGStatus:
    def test_status_ready_when_model_loaded(self, auth_client, monkeypatch):
        """模型已加载应返回 ready"""
        monkeypatch.setattr(
            "app.api.api_v1.endpoints.rag._embedding_service", object()
        )
        res = auth_client.get("/api/v1/rag/status")

        assert res.status_code == 200
        assert res.json() == {"status": "ready"}

    def test_status_loading_when_model_not_loaded(self, auth_client, monkeypatch):
        """模型未加载应返回 loading"""
        monkeypatch.setattr(
            "app.api.api_v1.endpoints.rag._embedding_service", None
        )
        res = auth_client.get("/api/v1/rag/status")

        assert res.status_code == 200
        assert res.json() == {"status": "loading"}

    def test_status_requires_auth(self):
        res = TestClient(app).get("/api/v1/rag/status")
        assert res.status_code == 403
