"""
异步入库处理器

将任务 payload 转换为实际的入库操作（解析 → 向量化 → 存储）。
"""

import asyncio
from typing import Dict, Any

from loguru import logger


async def process_ingestion_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    """处理入库任务（在 executor 中运行阻塞的嵌入与存储）"""
    title = payload.get("title", "未命名文档")
    content = payload.get("content", "")
    metadata = payload.get("metadata")
    current_user = payload.get("current_user") or {}

    if not content:
        raise ValueError("入库任务缺少内容")

    from app.api.api_v1.endpoints.rag import _do_upload

    loop = asyncio.get_event_loop()

    def _run():
        return _do_upload(title, content, metadata, current_user)

    result = await loop.run_in_executor(None, _run)
    logger.info(f"异步入库完成: {title}")
    return result
