"""
异步入库任务模型
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

JOB_PENDING = "pending"
JOB_PROCESSING = "processing"
JOB_DONE = "done"
JOB_ERROR = "error"


@dataclass
class IngestionJob:
    """入库任务"""
    id: str
    payload: Dict[str, Any]
    user_id: str
    status: str = JOB_PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }
