"""
速率限制模块
"""

from fastapi import Request, HTTPException, status
from typing import Dict, Optional
import time
from loguru import logger


class RateLimiter:
    """速率限制器"""

    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self._requests: Dict[str, list] = {}

    def _get_client_id(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用 X-Forwarded-For 头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        # 使用直连 IP
        return request.client.host if request.client else "unknown"

    def _clean_old_requests(self, client_id: str, current_time: float):
        """清理过期的请求记录"""
        if client_id not in self._requests:
            self._requests[client_id] = []

        # 清理超过1小时的记录
        self._requests[client_id] = [
            t for t in self._requests[client_id]
            if current_time - t < 3600
        ]

    def check(self, request: Request) -> bool:
        """检查是否超过速率限制"""
        client_id = self._get_client_id(request)
        current_time = time.time()

        self._clean_old_requests(client_id, current_time)

        # 检查每分钟限制
        minute_ago = current_time - 60
        recent_requests = sum(1 for t in self._requests[client_id] if t > minute_ago)
        if recent_requests >= self.requests_per_minute:
            logger.warning(f"速率限制触发（每分钟）: {client_id}")
            return False

        # 检查每小时限制
        if len(self._requests[client_id]) >= self.requests_per_hour:
            logger.warning(f"速率限制触发（每小时）: {client_id}")
            return False

        # 记录请求
        self._requests[client_id].append(current_time)
        return True


# 全局速率限制器实例
rate_limiter = RateLimiter(
    requests_per_minute=60,
    requests_per_hour=1000
)


async def check_rate_limit(request: Request):
    """速率限制依赖项"""
    if not rate_limiter.check(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试"
        )
