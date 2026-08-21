"""
RAG 文档删除越权漏洞修复测试（P4）

目标：
1. 用户可删自己的 private 文档 → 200
2. 用户删他人 private 文档 → 403
3. 非管理员删 system 文档 → 403
4. 管理员删任意文档 → 200
5. 删除不存在的 doc_id → 404（验证 fallback 已移除）
6. 未携带 token → 403
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.core.security import get_current_user


class FakeRecord:
    def __init__(self, point_id, payload):
        self.id = point_id
        self.payload = payload


class FakeVectorStore:
    def __init__(self, payloads):
        self._payloads = payloads
        self.deleted_ids = []
        self.client = None

    def get_all_records(self):
        return [FakeRecord(f"point-{i}", p) for i, p in enumerate(self._payloads)]

    def delete(self, ids):
        self.deleted_ids.extend(ids)
        return True


def _mock_rag_services(vector_store):
    return {
        "parser": None,
        "embedding": None,
        "vector_store": vector_store,
        "retriever": None,
        "generator": None,
    }


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class TestRagDeleteAuth:
    """rag.py DELETE /documents/{doc_id} 越权修复测试"""

    def _client(self, monkeypatch, user, payloads):
        async def override_auth():
            return user

        app.dependency_overrides[get_current_user] = override_auth

        store = FakeVectorStore(payloads)
        monkeypatch.setattr(
            "app.api.api_v1.endpoints.rag.get_rag_services",
            lambda: _mock_rag_services(store),
        )

        return TestClient(app), store

    def test_delete_own_private_document(self, monkeypatch):
        """用户可删自己的 private 文档"""
        user = {"user_id": "user-1", "email": "a@b.c", "is_admin": False}
        payloads = [
            {"doc_id": "doc-1", "scope": "private", "owner_id": "user-1", "content": "x"},
            {"doc_id": "doc-1", "scope": "private", "owner_id": "user-1", "content": "y"},
        ]
        client, store = self._client(monkeypatch, user, payloads)

        res = client.delete("/api/v1/rag/documents/doc-1")

        assert res.status_code == 200
        assert res.json()["chunks_deleted"] == 2
        assert store.deleted_ids == ["point-0", "point-1"]

    def test_delete_other_user_private_document_returns_403(self, monkeypatch):
        """非管理员删他人 private 文档 → 403，不执行删除"""
        user = {"user_id": "user-1", "email": "a@b.c", "is_admin": False}
        payloads = [
            {"doc_id": "doc-9", "scope": "private", "owner_id": "user-2", "content": "x"},
        ]
        client, store = self._client(monkeypatch, user, payloads)

        res = client.delete("/api/v1/rag/documents/doc-9")

        assert res.status_code == 403
        assert res.json()["detail"] == "无权删除该文档"
        assert store.deleted_ids == []

    def test_delete_system_document_by_non_admin_returns_403(self, monkeypatch):
        """非管理员删 system 文档 → 403"""
        user = {"user_id": "user-1", "email": "a@b.c", "is_admin": False}
        payloads = [
            {"doc_id": "sys-1", "scope": "system", "owner_id": None, "content": "x"},
        ]
        client, store = self._client(monkeypatch, user, payloads)

        res = client.delete("/api/v1/rag/documents/sys-1")

        assert res.status_code == 403
        assert store.deleted_ids == []

    def test_admin_can_delete_system_and_others(self, monkeypatch):
        """管理员可删 system 文档和他人 private 文档"""
        user = {"user_id": "admin-1", "email": "admin@outeye.com", "is_admin": True}
        payloads = [
            {"doc_id": "sys-1", "scope": "system", "owner_id": None, "content": "x"},
            {"doc_id": "priv-2", "scope": "private", "owner_id": "user-2", "content": "x"},
        ]
        client, store = self._client(monkeypatch, user, payloads)

        res1 = client.delete("/api/v1/rag/documents/sys-1")
        res2 = client.delete("/api/v1/rag/documents/priv-2")

        assert res1.status_code == 200
        assert res2.status_code == 200
        assert store.deleted_ids == ["point-0", "point-1"]

    def test_delete_nonexistent_returns_404(self, monkeypatch):
        """删除不存在的 doc_id → 404（fallback 已移除）"""
        user = {"user_id": "user-1", "email": "a@b.c", "is_admin": False}
        client, store = self._client(monkeypatch, user, [])

        res = client.delete("/api/v1/rag/documents/ghost")

        assert res.status_code == 404
        assert res.json()["detail"] == "文档不存在"
        assert store.deleted_ids == []

    def test_delete_requires_auth(self):
        """未携带 token → 403"""
        with patch("app.api.api_v1.endpoints.rag.get_rag_services") as mock_services:
            mock_services.return_value = {
                "parser": None, "embedding": None, "vector_store": None,
                "retriever": None, "generator": None,
            }
            client = TestClient(app)
            res = client.delete("/api/v1/rag/documents/doc-1")
            assert res.status_code == 403
