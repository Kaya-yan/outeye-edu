"""
knowledge.py 端点鉴权与 owner 过滤测试（P3）

目标：
1. 7 个端点未携带 token → 403
2. GET / 仅返回当前用户的 chunks
3. GET /theories/all 仅返回当前用户的理论
4. GET /strategies/all 仅返回当前用户的策略
5. GET /{chunk_id} 访问他人 chunk → 403
6. POST / 创建时 Document.user_id = current_user.user_id
7. POST /search 仅搜索当前用户的 chunks
8. POST /rag-query 仅基于当前用户的 chunks
9. 管理员可访问全部
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.core.security import get_current_user
from app.models.document import Document, DocumentChunk


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


async def _seed_two_users(test_db_session):
    """准备 user-1 和 user-2 的测试数据"""
    doc1 = Document(
        id="d-1", user_id="user-1", title="doc1", file_type="manual",
        status="indexed", created_at=datetime.utcnow(),
    )
    doc2 = Document(
        id="d-2", user_id="user-2", title="doc2", file_type="manual",
        status="indexed", created_at=datetime.utcnow(),
    )
    chunk1 = DocumentChunk(
        id="c-1", document_id="d-1", content="Krashen 输入假说 i+1",
        chunk_index=0, word_count=5,
        extra_data={"content_type": "theory", "source_type": "manual"},
        created_at=datetime.utcnow(),
    )
    chunk2 = DocumentChunk(
        id="c-2", document_id="d-2", content="他人私有 chunk 内容",
        chunk_index=0, word_count=4,
        extra_data={"content_type": "document", "source_type": "manual"},
        created_at=datetime.utcnow(),
    )
    test_db_session.add_all([doc1, doc2, chunk1, chunk2])
    await test_db_session.commit()


def _auth_as(user_id="user-1", is_admin=False):
    async def override_auth():
        return {"user_id": user_id, "email": "a@b.c", "is_admin": is_admin}
    app.dependency_overrides[get_current_user] = override_auth


class TestKnowledgeEndpointsAuth:
    """knowledge.py 7 个端点鉴权与 owner 过滤测试"""

    @pytest.mark.asyncio
    async def test_get_chunks_only_returns_own(self, test_db_session, client):
        """普通用户只能看到自己的 chunks"""
        await _seed_two_users(test_db_session)
        _auth_as("user-1")

        res = client.get("/api/v1/knowledge/")

        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["id"] == "c-1"

    @pytest.mark.asyncio
    async def test_get_chunks_as_admin_returns_all(self, test_db_session, client):
        """管理员可看到全部 chunks"""
        await _seed_two_users(test_db_session)
        _auth_as("admin-1", is_admin=True)

        res = client.get("/api/v1/knowledge/")

        assert res.status_code == 200
        assert len(res.json()) == 2

    @pytest.mark.asyncio
    async def test_get_theories_only_returns_own(self, test_db_session, client):
        """普通用户的 theories 列表只含自己的 theory 类型"""
        await _seed_two_users(test_db_session)
        _auth_as("user-1")

        res = client.get("/api/v1/knowledge/theories/all")

        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["id"] == "c-1"

    @pytest.mark.asyncio
    async def test_get_strategies_only_returns_own(self, test_db_session, client):
        """无 teaching_strategy 类型时应返回空列表"""
        await _seed_two_users(test_db_session)
        _auth_as("user-1")

        res = client.get("/api/v1/knowledge/strategies/all")

        assert res.status_code == 200
        assert res.json() == []

    @pytest.mark.asyncio
    async def test_get_chunk_by_id_other_user_returns_403(self, test_db_session, client):
        """访问他人 chunk → 403"""
        await _seed_two_users(test_db_session)
        _auth_as("user-1")

        res = client.get("/api/v1/knowledge/c-2")

        assert res.status_code == 403
        assert res.json()["detail"] == "无权访问该知识单元"

    @pytest.mark.asyncio
    async def test_get_chunk_by_id_own_returns_200(self, test_db_session, client):
        """访问自己的 chunk → 200"""
        await _seed_two_users(test_db_session)
        _auth_as("user-1")

        res = client.get("/api/v1/knowledge/c-1")

        assert res.status_code == 200
        assert res.json()["id"] == "c-1"

    @pytest.mark.asyncio
    async def test_get_chunk_by_id_admin_returns_200(self, test_db_session, client):
        """管理员访问他人 chunk → 200"""
        await _seed_two_users(test_db_session)
        _auth_as("admin-1", is_admin=True)

        res = client.get("/api/v1/knowledge/c-2")

        assert res.status_code == 200
        assert res.json()["id"] == "c-2"

    @pytest.mark.asyncio
    async def test_create_chunk_sets_owner(self, test_db_session, client):
        """创建 chunk 时 Document.user_id 应为 current_user.user_id"""
        _auth_as("user-99")

        res = client.post("/api/v1/knowledge/", json={
            "content": "新建的知识单元内容",
            "content_type": "theory",
            "source_type": "manual",
        })

        assert res.status_code == 200
        chunk_id = res.json()["id"]

        chunk = (await test_db_session.execute(
            select(DocumentChunk).where(DocumentChunk.id == chunk_id)
        )).scalar_one()
        doc = (await test_db_session.execute(
            select(Document).where(Document.id == chunk.document_id)
        )).scalar_one()
        assert doc.user_id == "user-99"

    @pytest.mark.asyncio
    async def test_search_does_not_return_other_user_chunks(self, test_db_session, client):
        """搜索不应返回他人的 chunks（即使内容匹配）"""
        await _seed_two_users(test_db_session)
        _auth_as("user-1")

        # "chunk" 关键词只出现在 user-2 的 c-2 中
        res = client.post("/api/v1/knowledge/search", json={
            "query": "chunk", "top_k": 5,
        })

        assert res.status_code == 200
        assert res.json() == []

    @pytest.mark.asyncio
    async def test_search_finds_own_content(self, test_db_session, client):
        """搜索应返回自己的 chunks"""
        await _seed_two_users(test_db_session)
        _auth_as("user-1")

        res = client.post("/api/v1/knowledge/search", json={
            "query": "Krashen", "top_k": 5,
        })

        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["chunk_id"] == "c-1"

    @pytest.mark.asyncio
    async def test_rag_query_only_uses_own_chunks(self, test_db_session, client):
        """rag-query 只应基于当前用户的 chunks"""
        await _seed_two_users(test_db_session)
        _auth_as("user-1")

        res = client.post("/api/v1/knowledge/rag-query?query=Krashen&top_k=5")

        assert res.status_code == 200
        data = res.json()
        assert len(data["retrieved_chunks"]) == 1
        assert data["retrieved_chunks"][0]["chunk_id"] == "c-1"

    def test_all_endpoints_require_token(self):
        """7 个端点未携带 token → 403"""
        client = TestClient(app)
        cases = [
            ("GET", "/api/v1/knowledge/", None),
            ("GET", "/api/v1/knowledge/theories/all", None),
            ("GET", "/api/v1/knowledge/strategies/all", None),
            ("GET", "/api/v1/knowledge/c-1", None),
            ("POST", "/api/v1/knowledge/", {"content": "x", "content_type": "theory"}),
            ("POST", "/api/v1/knowledge/search", {"query": "x"}),
            ("POST", "/api/v1/knowledge/rag-query?query=x", None),
        ]
        for method, path, body in cases:
            if method == "GET":
                res = client.get(path)
            else:
                res = client.post(path, json=body) if body else client.post(path)
            assert res.status_code == 403, (
                f"{method} {path} 应返回 403，实际 {res.status_code}"
            )
