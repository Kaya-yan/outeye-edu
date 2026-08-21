"""
RAG 入库任务归属检查测试（P5）

目标：
1. 用户可查自己的 job → 200
2. 用户查他人 job → 403
3. 管理员可查任何 job → 200
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


def _client_as(user):
    async def override_auth():
        return user

    app.dependency_overrides[get_current_user] = override_auth
    return TestClient(app)


def _patch_queue(monkeypatch, job, allow_job_id="job-1"):
    class FakeQueue:
        def get(self, job_id):
            if job_id == allow_job_id:
                return job
            return None

    monkeypatch.setattr(
        "app.services.ingestion.queue.ingestion_queue", FakeQueue()
    )


class TestJobsAuth:
    """rag.py GET /jobs/{job_id} 归属检查测试"""

    def test_get_own_job_returns_200(self, monkeypatch):
        """用户查自己的 job → 200"""
        user = {"user_id": "user-1", "email": "a@b.c", "is_admin": False}
        job = IngestionJob(
            id="job-1", payload={}, user_id="user-1",
            stage="embedding", progress={"processed_chunks": 2, "total_chunks": 5},
        )
        _patch_queue(monkeypatch, job, "job-1")

        client = _client_as(user)
        res = client.get("/api/v1/rag/jobs/job-1")

        assert res.status_code == 200
        assert res.json()["stage"] == "embedding"

    def test_get_other_user_job_returns_403(self, monkeypatch):
        """用户查他人 job → 403"""
        user = {"user_id": "user-1", "email": "a@b.c", "is_admin": False}
        job = IngestionJob(
            id="job-2", payload={}, user_id="user-2",  # 他人 job
        )
        _patch_queue(monkeypatch, job, "job-2")

        client = _client_as(user)
        res = client.get("/api/v1/rag/jobs/job-2")

        assert res.status_code == 403
        assert res.json()["detail"] == "无权查看该任务"

    def test_admin_can_get_any_job(self, monkeypatch):
        """管理员可查任何 job → 200"""
        admin = {"user_id": "admin-1", "email": "admin@outeye.com", "is_admin": True}
        job = IngestionJob(
            id="job-3", payload={}, user_id="user-2",  # 他人 job
            stage="done",
        )
        _patch_queue(monkeypatch, job, "job-3")

        client = _client_as(admin)
        res = client.get("/api/v1/rag/jobs/job-3")

        assert res.status_code == 200
        assert res.json()["stage"] == "done"
