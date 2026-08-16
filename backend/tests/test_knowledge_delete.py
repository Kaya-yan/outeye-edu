"""
知识库文档删除测试（TDD）

目标：
1. 删除自己的 private 文档 → 200，Qdrant chunks + PG 记录清理
2. 删除他人 private / system 文档（非管理员）→ 403
3. 管理员可删除任意文档
4. 删除不存在 → 404，未认证 → 403
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_async_db
from app.core.security import get_current_user


class FakeRecord:
    def __init__(self, point_id, payload):
        self.id = point_id
        self.payload = payload


class FakeVectorStore:
    def __init__(self, payloads):
        self._payloads = payloads
        self.deleted_ids = []

    def get_all_records(self):
        return [FakeRecord(f"point-{i}", p) for i, p in enumerate(self._payloads)]

    def delete(self, ids):
        self.deleted_ids.extend(ids)
        return True


class FakeDBSession:
    def __init__(self):
        self.executed = []

    async def execute(self, stmt):
        self.executed.append(stmt)
        return type("R", (), {"rowcount": 0})()

    async def commit(self):
        pass


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class TestDeleteKnowledgeDocument:
    def _client(self, monkeypatch, user, payloads):
        async def override_auth():
            return user

        app.dependency_overrides[get_current_user] = override_auth

        db = FakeDBSession()

        async def override_db():
            yield db

        app.dependency_overrides[get_async_db] = override_db

        store = FakeVectorStore(payloads)
        monkeypatch.setattr(
            "app.api.api_v1.endpoints.knowledge._get_vector_store", lambda: store
        )

        return TestClient(app), store, db

    def test_delete_own_private_document(self, monkeypatch):
        user = {"user_id": "user-1", "email": "a@b.c", "is_admin": False}
        payloads = [
            {"doc_id": "doc-1", "scope": "private", "owner_id": "user-1", "content": "x"},
            {"doc_id": "doc-1", "scope": "private", "owner_id": "user-1", "content": "y"},
        ]
        client, store, db = self._client(monkeypatch, user, payloads)

        res = client.delete("/api/v1/knowledge/documents/doc-1")

        assert res.status_code == 200
        assert res.json()["deleted_chunks"] == 2
        assert store.deleted_ids == ["point-0", "point-1"]
        # 两次 PG DELETE：先 chunks 后 documents
        assert len(db.executed) == 2

    def test_delete_other_user_document_returns_403(self, monkeypatch):
        user = {"user_id": "user-1", "email": "a@b.c", "is_admin": False}
        payloads = [
            {"doc_id": "doc-9", "scope": "private", "owner_id": "user-2", "content": "x"},
        ]
        client, store, db = self._client(monkeypatch, user, payloads)

        res = client.delete("/api/v1/knowledge/documents/doc-9")

        assert res.status_code == 403
        assert store.deleted_ids == []

    def test_delete_system_document_by_non_admin_returns_403(self, monkeypatch):
        user = {"user_id": "user-1", "email": "a@b.c", "is_admin": False}
        payloads = [
            {"doc_id": "sys-1", "scope": "system", "owner_id": None, "content": "x"},
        ]
        client, store, db = self._client(monkeypatch, user, payloads)

        res = client.delete("/api/v1/knowledge/documents/sys-1")

        assert res.status_code == 403
        assert store.deleted_ids == []

    def test_admin_can_delete_any_document(self, monkeypatch):
        user = {"user_id": "admin-1", "email": "admin@outlook.com", "is_admin": True}
        payloads = [
            {"doc_id": "sys-1", "scope": "system", "owner_id": None, "content": "x"},
        ]
        client, store, db = self._client(monkeypatch, user, payloads)

        res = client.delete("/api/v1/knowledge/documents/sys-1")

        assert res.status_code == 200
        assert store.deleted_ids == ["point-0"]

    def test_delete_nonexistent_returns_404(self, monkeypatch):
        user = {"user_id": "user-1", "email": "a@b.c", "is_admin": False}
        client, store, db = self._client(monkeypatch, user, [])

        res = client.delete("/api/v1/knowledge/documents/ghost")

        assert res.status_code == 404

    def test_delete_requires_auth(self):
        res = TestClient(app).delete("/api/v1/knowledge/documents/doc-1")
        assert res.status_code == 403
