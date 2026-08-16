"""
异步入库队列

使用 asyncio.Queue + 单线程 worker（受限于 3.4GB 内存服务器，不引入 Celery）。
"""

import asyncio
from typing import Awaitable, Callable, Dict, Optional

from loguru import logger

from app.services.ingestion.jobs import (
    IngestionJob,
    JOB_PENDING,
    JOB_PROCESSING,
    JOB_DONE,
    JOB_ERROR,
    STAGE_DONE,
    STAGE_ERROR,
)
from app.services.ingestion.errors import IngestionError


class IngestionQueue:
    """入库任务队列"""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._jobs: Dict[str, IngestionJob] = {}

    async def submit(self, job: IngestionJob) -> str:
        """提交任务，返回 job_id"""
        self._jobs[job.id] = job
        await self._queue.put(job.id)
        return job.id

    def get(self, job_id: str) -> Optional[IngestionJob]:
        """查询任务状态"""
        return self._jobs.get(job_id)

    async def worker(self, processor: Callable[..., Awaitable[Dict]]):
        """单线程 worker：顺序消费队列，调用 processor 处理任务"""
        while True:
            job_id = await self._queue.get()
            job = self._jobs.get(job_id)
            if job is None:
                self._queue.task_done()
                continue

            job.status = JOB_PROCESSING

            def progress_callback(stage: str, progress: Optional[Dict[str, int]] = None):
                job.stage = stage
                if progress is not None:
                    job.progress = progress

            try:
                job.result = await processor(job.payload, progress_callback=progress_callback)
                job.status = JOB_DONE
                job.stage = STAGE_DONE
                logger.info(f"入库任务完成: {job_id}")
            except IngestionError as e:
                job.status = JOB_ERROR
                job.stage = STAGE_ERROR
                job.error = str(e)
                job.error_code = e.error_code
                logger.error(f"入库任务失败: {job_id}: [{e.error_code}] {e}")
            except Exception as e:
                job.status = JOB_ERROR
                job.stage = STAGE_ERROR
                job.error = str(e)
                logger.error(f"入库任务失败: {job_id}: {e}")
            finally:
                self._queue.task_done()


# 全局队列实例
ingestion_queue = IngestionQueue()
