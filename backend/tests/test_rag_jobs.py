"""
RAG 入库任务状态查询测试（TDD）

目标：GET /rag/jobs/{job_id} 返回 stage 与 progress。
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import get_current_user
from app.services.ingestion.jobs import IngestionJob


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


class TestJobStatusEndpoint:
    def test_job_status_returns_stage_and_progress(self, auth_client, monkeypatch):
        job = IngestionJob(
            id="job-1", payload={}, user_id="user-1",
            stage="embedding", progress={"processed_chunks": 2, "total_chunks": 5},
        )

        class FakeQueue:
            def get(self, job_id):
                return job if job_id == "job-1" else None

        monkeypatch.setattr(
            "app.services.ingestion.queue.ingestion_queue", FakeQueue()
        )

        res = auth_client.get("/api/v1/rag/jobs/job-1")

        assert res.status_code == 200
        body = res.json()
        assert body["stage"] == "embedding"
        assert body["progress"] == {"processed_chunks": 2, "total_chunks": 5}

    def test_job_status_returns_error_code(self, auth_client, monkeypatch):
        job = IngestionJob(
            id="job-2", payload={}, user_id="user-1",
            status="error", error_code="SCANNED_PDF", error="扫描件无法自动解析",
        )

        class FakeQueue:
            def get(self, job_id):
                return job if job_id == "job-2" else None

        monkeypatch.setattr(
            "app.services.ingestion.queue.ingestion_queue", FakeQueue()
        )

        res = auth_client.get("/api/v1/rag/jobs/job-2")

        assert res.status_code == 200
        assert res.json()["error_code"] == "SCANNED_PDF"

    def test_job_status_returns_404_for_missing(self, auth_client, monkeypatch):
        class FakeQueue:
            def get(self, job_id):
                return None

        monkeypatch.setattr(
            "app.services.ingestion.queue.ingestion_queue", FakeQueue()
        )

        res = auth_client.get("/api/v1/rag/jobs/ghost")

        assert res.status_code == 404
