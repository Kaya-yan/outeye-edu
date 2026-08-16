"""
异步知识入库队列测试（TDD）

目标：
1. 上传提交为异步任务，立即返回 job_id（status=pending）
2. worker 顺序处理任务，状态 pending → processing → done/error
3. 任务结果可查询
"""

import asyncio
import uuid

import pytest

from app.services.ingestion.jobs import IngestionJob, JOB_PENDING, JOB_DONE, JOB_ERROR
from app.services.ingestion.queue import IngestionQueue


class TestIngestionQueue:
    """异步入库队列测试"""

    def make_job(self, payload=None):
        return IngestionJob(
            id=str(uuid.uuid4()),
            payload=payload or {"title": "test", "content": "hello"},
            user_id="user-1",
        )

    @pytest.mark.asyncio
    async def test_submit_returns_job_id_with_pending_status(self):
        """提交任务应立即返回 job_id 且状态为 pending"""
        queue = IngestionQueue()
        job = self.make_job()

        job_id = await queue.submit(job)

        assert job_id == job.id
        assert queue.get(job_id).status == JOB_PENDING

    @pytest.mark.asyncio
    async def test_worker_processes_jobs_sequentially(self):
        """worker 应按顺序处理任务并更新状态"""
        queue = IngestionQueue()

        processed_order = []

        async def processor(payload):
            processed_order.append(payload["title"])
            await asyncio.sleep(0.01)
            return {"ok": True}

        job1 = self.make_job({"title": "first", "content": "a"})
        job2 = self.make_job({"title": "second", "content": "b"})
        await queue.submit(job1)
        await queue.submit(job2)

        # 启动 worker 并处理两个任务后停止
        worker_task = asyncio.create_task(queue.worker(processor))
        # 等待两个任务处理完成
        for _ in range(2):
            await asyncio.sleep(0.05)

        assert processed_order == ["first", "second"]
        assert queue.get(job1.id).status == JOB_DONE
        assert queue.get(job2.id).status == JOB_DONE
        assert queue.get(job1.id).result == {"ok": True}

        worker_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker_task

    @pytest.mark.asyncio
    async def test_worker_marks_error_on_exception(self):
        """处理异常时任务状态应标记为 error"""
        queue = IngestionQueue()

        async def failing_processor(payload):
            raise RuntimeError("boom")

        job = self.make_job()
        await queue.submit(job)

        worker_task = asyncio.create_task(queue.worker(failing_processor))
        await asyncio.sleep(0.05)

        assert queue.get(job.id).status == JOB_ERROR
        assert "boom" in queue.get(job.id).error

        worker_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker_task

    @pytest.mark.asyncio
    async def test_get_missing_job_returns_none(self):
        """查询不存在的任务应返回 None"""
        queue = IngestionQueue()
        assert queue.get("nonexistent") is None
