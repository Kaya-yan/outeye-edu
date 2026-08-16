"""
知识库文件上传测试（TDD）

目标：
1. POST /api/v1/knowledge/upload 接受 multipart 文件，返回 202 {document_id, status:"queued"}
2. 拒绝 .doc 与不支持扩展名
3. 文件处理器解析文件并以 private 作用域写入向量库
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import get_current_user


@pytest.fixture
def auth_client():
    async def override_auth():
        return {"user_id": "user-1", "email": "test@example.com", "is_admin": False}

    app.dependency_overrides[get_current_user] = override_auth
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestKnowledgeUploadEndpoint:
    """知识库文件上传端点测试"""

    def test_upload_returns_202_queued(self, auth_client, monkeypatch):
        """上传应返回 202 并入队"""
        submitted = {}

        async def fake_submit(job):
            submitted["job"] = job
            return job.id

        monkeypatch.setattr(
            "app.services.ingestion.queue.ingestion_queue.submit", fake_submit
        )

        res = auth_client.post(
            "/api/v1/knowledge/upload",
            files={"file": ("lesson.txt", b"hello world content", "text/plain")},
        )

        assert res.status_code == 202
        body = res.json()
        assert body["status"] == "queued"
        assert body["document_id"] == submitted["job"].id
        assert submitted["job"].payload["filename"] == "lesson.txt"
        assert submitted["job"].payload["type"] == "file"

    def test_upload_rejects_doc_extension(self, auth_client):
        """旧 .doc 应拒绝并提示转存"""
        res = auth_client.post(
            "/api/v1/knowledge/upload",
            files={"file": ("legacy.doc", b"content", "application/msword")},
        )
        assert res.status_code == 400
        assert "另存为" in res.json()["detail"]

    def test_upload_rejects_bad_extension(self, auth_client):
        """不支持扩展名应拒绝"""
        res = auth_client.post(
            "/api/v1/knowledge/upload",
            files={"file": ("movie.mp4", b"content", "video/mp4")},
        )
        assert res.status_code == 400

    def test_upload_rejects_oversized(self, auth_client, monkeypatch):
        """超大小文件应拒绝"""
        monkeypatch.setattr(
            "app.api.api_v1.endpoints.knowledge.KNOWLEDGE_MAX_UPLOAD_SIZE", 10
        )
        res = auth_client.post(
            "/api/v1/knowledge/upload",
            files={"file": ("big.txt", b"x" * 100, "text/plain")},
        )
        assert res.status_code == 400

    def test_upload_requires_auth(self):
        """未认证应拒绝"""
        res = TestClient(app).post(
            "/api/v1/knowledge/upload",
            files={"file": ("lesson.txt", b"hello", "text/plain")},
        )
        assert res.status_code == 403


class TestFileIngestionProcessor:
    """文件处理器测试"""

    def test_ingest_file_stores_with_scope(self, monkeypatch):
        """文件处理器应以 private 作用域写入"""
        from app.services.ingestion.processor import _ingest_file_sync

        class FakeChunk:
            def __init__(self):
                self.id = "chunk-1"
                self.doc_id = "parser-doc-id"
                self.content = "hello"
                self.metadata = {}

        class FakeDoc:
            id = "parser-doc-id"
            title = "lesson.txt"
            chunks = [FakeChunk()]

        class FakeParser:
            def parse_file(self, path):
                return FakeDoc()

        class FakeEmbedding:
            def embed_text(self, text):
                return type("R", (), {"embedding": [0.1, 0.2, 0.3]})()

        class FakeVectorStore:
            def __init__(self):
                self.records = []

            def upsert(self, records):
                self.records.extend(records)
                return True

        fake_store = FakeVectorStore()
        monkeypatch.setattr(
            "app.api.api_v1.endpoints.rag.get_rag_services",
            lambda: {
                "parser": FakeParser(),
                "embedding": FakeEmbedding(),
                "vector_store": fake_store,
                "retriever": None,
                "generator": None,
            },
        )

        result = _ingest_file_sync(
            "lesson.txt", b"hello world", "doc-123", {"user_id": "user-1"}
        )

        assert result["success"] is True
        assert len(fake_store.records) == 1
        # 用上传时的 document_id，而非 parser 的 doc_id
        assert fake_store.records[0].payload["doc_id"] == "doc-123"
        assert fake_store.records[0].payload["scope"] == "private"
        assert fake_store.records[0].payload["owner_id"] == "user-1"
