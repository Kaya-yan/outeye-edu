"""
异步知识入库服务
"""

from app.services.ingestion.jobs import (
    IngestionJob,
    JOB_PENDING,
    JOB_PROCESSING,
    JOB_DONE,
    JOB_ERROR,
    STAGE_RECEIVED,
    STAGE_PARSING,
    STAGE_CHUNKING,
    STAGE_EMBEDDING,
    STAGE_DONE,
    STAGE_ERROR,
)
from app.services.ingestion.queue import IngestionQueue

__all__ = [
    "IngestionJob",
    "IngestionQueue",
    "JOB_PENDING",
    "JOB_PROCESSING",
    "JOB_DONE",
    "JOB_ERROR",
    "STAGE_RECEIVED",
    "STAGE_PARSING",
    "STAGE_CHUNKING",
    "STAGE_EMBEDDING",
    "STAGE_DONE",
    "STAGE_ERROR",
]
