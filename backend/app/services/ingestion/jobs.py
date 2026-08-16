"""
异步入库任务模型
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

JOB_PENDING = "pending"
JOB_PROCESSING = "processing"
JOB_DONE = "done"
JOB_ERROR = "error"

# 细粒度处理阶段
STAGE_RECEIVED = "received"
STAGE_PARSING = "parsing"
STAGE_CHUNKING = "chunking"
STAGE_EMBEDDING = "embedding"
STAGE_DONE = "done"
STAGE_ERROR = "error"


@dataclass
class IngestionJob:
    """入库任务"""
    id: str
    payload: Dict[str, Any]
    user_id: str
    status: str = JOB_PENDING
    stage: str = STAGE_RECEIVED
    progress: Optional[Dict[str, int]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "error_code": self.error_code,
        }
