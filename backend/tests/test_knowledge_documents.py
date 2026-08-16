"""
知识库文档列表测试（TDD）

目标：
1. GET /api/v1/knowledge/documents?scope=system 返回所有 system 文档
2. scope=private 仅返回当前用户的 private 文档
3. 需认证，非法 scope 返回 400
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import get_current_user


class FakeRecord:
    def __init__(self, payload):
        self.payload = payload


class FakeStore:
    def __init__(self, payloads):
        self._payloads = payloads

    def get_all_records(self):
        return [FakeRecord(p) for p in self._payloads]


@pytest.fixture
def auth_client(monkeypatch):
    async def override_auth():
        return {"user_id": "user-1", "email": "test@example.com", "is_admin": False}

    app.dependency_overrides[get_current_user] = override_auth
    yield TestClient(app)
    app.dependency_overrides.clear()


def _patch_store(monkeypatch, payloads):
    monkeypatch.setattr(
        "app.api.api_v1.endpoints.knowledge._get_vector_store",
        lambda: FakeStore(payloads),
    )


class TestListKnowledgeDocuments:
    """文档列表测试"""

    def test_list_system_documents_groups_by_doc_id(self, auth_client, monkeypatch):
        payloads = [
            {"doc_id": "sys-1", "title": "Krashen 输入假说", "scope": "system",
             "owner_id": None, "source": "system_seed", "doc_type": "theory",
             "tags": ["输入假说"], "content": "chunk1 内容", "created_at": "2026-08-16T00:00:00"},
            {"doc_id": "sys-1", "title": "Krashen 输入假说", "scope": "system",
             "owner_id": None, "source": "system_seed", "doc_type": "theory",
             "tags": ["输入假说"], "content": "chunk2 内容", "created_at": "2026-08-16T00:00:00"},
            {"doc_id": "sys-2", "title": "Bloom 分类", "scope": "system",
             "owner_id": None, "source": "system_seed", "doc_type": "theory",
             "tags": ["认知目标"], "content": "bloom 内容", "created_at": "2026-08-16T00:00:00"},
        ]
        _patch_store(monkeypatch, payloads)

        res = auth_client.get("/api/v1/knowledge/documents?scope=system")

        assert res.status_code == 200
        docs = res.json()
        assert len(docs) == 2
        by_id = {d["id"]: d for d in docs}
        assert by_id["sys-1"]["title"] == "Krashen 输入假说"
        assert by_id["sys-1"]["doc_type"] == "theory"
        assert by_id["sys-1"]["tags"] == ["输入假说"]
        assert by_id["sys-1"]["status"] == "indexed"

    def test_list_private_documents_filters_by_owner(self, auth_client, monkeypatch):
        payloads = [
            {"doc_id": "p-1", "title": "我的资料1", "scope": "private", "owner_id": "user-1",
             "source": "user_upload", "doc_type": "document", "tags": [], "content": "content1"},
            {"doc_id": "p-2", "title": "他人资料", "scope": "private", "owner_id": "user-2",
             "source": "user_upload", "doc_type": "document", "tags": [], "content": "content2"},
        ]
        _patch_store(monkeypatch, payloads)

        res = auth_client.get("/api/v1/knowledge/documents?scope=private")

        assert res.status_code == 200
        docs = res.json()
        assert len(docs) == 1
        assert docs[0]["id"] == "p-1"

    def test_list_invalid_scope_returns_400(self, auth_client, monkeypatch):
        _patch_store(monkeypatch, [])

        res = auth_client.get("/api/v1/knowledge/documents?scope=other")

        assert res.status_code == 400

    def test_list_requires_auth(self):
        res = TestClient(app).get("/api/v1/knowledge/documents?scope=system")
        assert res.status_code == 403
