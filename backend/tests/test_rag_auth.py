"""
RAG 端点权限测试（TDD）

目标：所有 RAG 端点必须要求认证。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app


@pytest.fixture
def client_no_auth():
    """提供 TestClient，但不注入任何认证依赖覆盖"""
    with patch("app.api.api_v1.endpoints.rag.get_rag_services") as mock_services:
        # 提供一个最小 mock，避免服务初始化
        mock_services.return_value = {
            "parser": None,
            "embedding": None,
            "vector_store": None,
            "retriever": None,
            "generator": None,
        }
        yield TestClient(app)


class TestRAGAuthentication:
    """RAG 端点认证测试"""

    # FastAPI HTTPBearer 在没有 Authorization 头时返回 403
    UNAUTHENTICATED_STATUS = 403

    def test_upload_without_token_returns_403(self, client_no_auth):
        """未携带 Token 访问 /rag/upload 应被拒绝"""
        response = client_no_auth.post(
            "/api/v1/rag/upload",
            json={"title": "Test", "content": "Hello world"},
        )
        assert response.status_code == self.UNAUTHENTICATED_STATUS

    def test_upload_file_without_token_returns_403(self, client_no_auth):
        """未携带 Token 访问 /rag/upload-file 应被拒绝"""
        response = client_no_auth.post(
            "/api/v1/rag/upload-file",
            data={},
        )
        assert response.status_code == self.UNAUTHENTICATED_STATUS

    def test_query_without_token_returns_403(self, client_no_auth):
        """未携带 Token 访问 /rag/query 应被拒绝"""
        response = client_no_auth.post(
            "/api/v1/rag/query",
            json={"query": "test"},
        )
        assert response.status_code == self.UNAUTHENTICATED_STATUS

    def test_query_with_wiki_without_token_returns_403(self, client_no_auth):
        """未携带 Token 访问 /rag/query-with-wiki 应被拒绝"""
        response = client_no_auth.post(
            "/api/v1/rag/query-with-wiki",
            json={"query": "test"},
        )
        assert response.status_code == self.UNAUTHENTICATED_STATUS

    def test_delete_document_without_token_returns_403(self, client_no_auth):
        """未携带 Token 访问 /rag/documents/{id} DELETE 应被拒绝"""
        response = client_no_auth.delete("/api/v1/rag/documents/doc-123")
        assert response.status_code == self.UNAUTHENTICATED_STATUS

    def test_search_similar_without_token_returns_403(self, client_no_auth):
        """未携带 Token 访问 /rag/search-similar 应被拒绝"""
        response = client_no_auth.post(
            "/api/v1/rag/search-similar",
            params={"text": "test", "top_k": 5},
        )
        assert response.status_code == self.UNAUTHENTICATED_STATUS

    def test_stats_without_token_returns_403(self, client_no_auth):
        """未携带 Token 访问 /rag/stats 应被拒绝"""
        response = client_no_auth.get("/api/v1/rag/stats")
        assert response.status_code == self.UNAUTHENTICATED_STATUS
