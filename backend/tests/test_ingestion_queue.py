"""
异步知识入库队列测试（TDD）

目标：
1. 上传提交为异步任务，立即返回 job_id（status=pending）
2. worker 顺序处理任务，状态 pending → processing → done/error
3. 任务阶段 stage 从 received → done/error
4. 任务结果可查询
"""

import asyncio
import uuid

import pytest

from app.services.ingestion.jobs import (
    IngestionJob,
    JOB_PENDING,
    JOB_DONE,
    JOB_ERROR,
    STAGE_RECEIVED,
    STAGE_DONE,
    STAGE_ERROR,
)
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
        assert queue.get(job_id).stage == STAGE_RECEIVED

    @pytest.mark.asyncio
    async def test_worker_processes_jobs_sequentially(self):
        """worker 应按顺序处理任务并更新状态"""
        queue = IngestionQueue()

        processed_order = []

        async def processor(payload, progress_callback=None):
            processed_order.append(payload["title"])
            await asyncio.sleep(0.01)
            return {"ok": True}

        job1 = self.make_job({"title": "first", "content": "a"})
        job2 = self.make_job({"title": "second", "content": "b"})
        await queue.submit(job1)
        await queue.submit(job2)

        worker_task = asyncio.create_task(queue.worker(processor))
        for _ in range(2):
            await asyncio.sleep(0.05)

        assert processed_order == ["first", "second"]
        assert queue.get(job1.id).status == JOB_DONE
        assert queue.get(job1.id).stage == STAGE_DONE
        assert queue.get(job1.id).result == {"ok": True}

        worker_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker_task

    @pytest.mark.asyncio
    async def test_worker_marks_error_on_exception(self):
        """处理异常时任务状态应标记为 error，stage=error"""
        queue = IngestionQueue()

        async def failing_processor(payload, progress_callback=None):
            raise RuntimeError("boom")

        job = self.make_job()
        await queue.submit(job)

        worker_task = asyncio.create_task(queue.worker(failing_processor))
        await asyncio.sleep(0.05)

        assert queue.get(job.id).status == JOB_ERROR
        assert queue.get(job.id).stage == STAGE_ERROR
        assert "boom" in queue.get(job.id).error

        worker_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker_task

    @pytest.mark.asyncio
    async def test_worker_passes_progress_callback(self):
        """worker 应向 processor 传入 progress_callback，阶段更新到 job"""
        queue = IngestionQueue()

        async def processor(payload, progress_callback=None):
            progress_callback("embedding", {"processed_chunks": 1, "total_chunks": 3})
            return {"ok": True}

        job = self.make_job()
        await queue.submit(job)

        worker_task = asyncio.create_task(queue.worker(processor))
        await asyncio.sleep(0.05)

        # 完成后 stage 被 worker 覆盖为 done
        assert queue.get(job.id).stage == STAGE_DONE
        # 但 progress 被回调写入并保留
        assert queue.get(job.id).progress == {"processed_chunks": 1, "total_chunks": 3}

        worker_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker_task

    @pytest.mark.asyncio
    async def test_worker_sets_error_code(self):
        """processor 抛 IngestionError 时应写入 error_code"""
        from app.services.ingestion.errors import IngestionError, ERROR_SCANNED_PDF

        queue = IngestionQueue()

        async def processor(payload, progress_callback=None):
            raise IngestionError(ERROR_SCANNED_PDF)

        job = self.make_job()
        await queue.submit(job)

        worker_task = asyncio.create_task(queue.worker(processor))
        await asyncio.sleep(0.05)

        assert queue.get(job.id).status == JOB_ERROR
        assert queue.get(job.id).error_code == ERROR_SCANNED_PDF

        worker_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker_task

    @pytest.mark.asyncio
    async def test_get_missing_job_returns_none(self):
        """查询不存在的任务应返回 None"""
        queue = IngestionQueue()
        assert queue.get("nonexistent") is None
