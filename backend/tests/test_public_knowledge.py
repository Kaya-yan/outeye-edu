"""任务F3 公共资料详情测试：builtin 长文 / 官方语料分片聚合排序 / 404 / 鉴权"""

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


class TestPublicKnowledgeDetail:
    def test_builtin_asset_returns_long_detail(self, auth_client):
        res = auth_client.get("/api/v1/knowledge/public/builtin-teaching-theories")
        assert res.status_code == 200
        body = res.json()
        assert body["kind"] == "builtin"
        assert body["chunk_count"] == 0
        assert len(body["detail"]) > 200  # 内置长文说明，而非摘要
        assert body["title"]

    def test_document_chunks_aggregated_in_order(self, auth_client, monkeypatch):
        payloads = [
            {"doc_id": "sys-9", "title": "体裁教学指南", "scope": "system",
             "chunk_index": 1, "doc_type": "theory", "content": "第二段正文",
             "created_at": "2026-08-16T00:00:00"},
            {"doc_id": "sys-9", "title": "体裁教学指南", "scope": "system",
             "chunk_index": 0, "doc_type": "theory", "content": "第一段正文",
             "created_at": "2026-08-16T00:00:00"},
            # 同 doc_id 的私有语料不得泄入公共详情
            {"doc_id": "sys-9", "title": "私有语料", "scope": "private", "owner_id": "user-2",
             "chunk_index": 2, "doc_type": "document", "content": "私有内容"},
        ]
        _patch_store(monkeypatch, payloads)

        res = auth_client.get("/api/v1/knowledge/public/sys-9")
        assert res.status_code == 200
        body = res.json()
        assert body["kind"] == "document"
        assert body["chunk_count"] == 2
        # 按 chunk_index 排序后拼接
        assert body["detail"] == "第一段正文\n\n第二段正文"
        assert body["title"] == "体裁教学指南"

    def test_unknown_id_returns_404(self, auth_client, monkeypatch):
        _patch_store(monkeypatch, [])
        res = auth_client.get("/api/v1/knowledge/public/no-such-item")
        assert res.status_code == 404

    def test_requires_auth(self):
        res = TestClient(app).get("/api/v1/knowledge/public/builtin-cefr-wordlists")
        assert res.status_code == 403


class TestPublicKnowledgeExcerpt:
    """任务G1：列表摘要与详情超长时按句边界修剪，头部加（节选）"""

    def test_list_summary_trimmed_to_sentence(self, auth_client, monkeypatch):
        long_content = "这部分是完整的句子，讲教学理论的核心观点。" * 20
        _patch_store(monkeypatch, [{
            "doc_id": "sys-x", "title": "句界测试语料", "scope": "system",
            "chunk_index": 0, "doc_type": "theory", "content": long_content,
            "created_at": "2026-09-14T00:00:00",
        }])

        res = auth_client.get("/api/v1/knowledge/public")
        assert res.status_code == 200
        doc = next(i for i in res.json() if i.get("id") == "sys-x")
        assert doc["summary"].startswith("（节选）")
        assert doc["summary"].endswith("。")

    def test_detail_trimmed_with_marker_when_over_limit(self, auth_client, monkeypatch):
        content = "这是一段足够长的正文句子，用于超过详情截断上限的测试。" * 400
        _patch_store(monkeypatch, [{
            "doc_id": "sys-y", "title": "长文语料", "scope": "system",
            "chunk_index": 0, "doc_type": "theory", "content": content,
        }])

        res = auth_client.get("/api/v1/knowledge/public/sys-y")
        assert res.status_code == 200
        body = res.json()
        assert body["detail"].startswith("（节选）")
        assert body["detail"].endswith("。")
