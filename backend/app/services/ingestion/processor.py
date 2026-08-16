"""
异步入库处理器

将任务 payload 转换为实际的入库操作（解析 → 向量化 → 存储）。
按 payload.type 分发：file（文件）或 text（文本，默认）。
通过 progress_callback 上报细粒度阶段（parsing/chunking/embedding）。
"""

import asyncio
import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable

from loguru import logger

from app.services.ingestion.jobs import (
    STAGE_PARSING,
    STAGE_CHUNKING,
    STAGE_EMBEDDING,
)
from app.services.ingestion.errors import (
    IngestionError,
    ERROR_SCANNED_PDF,
    ERROR_WORD_PARSE_FAILED,
    ERROR_TEXT_ENCODING_FAILED,
    ERROR_EMBEDDING_WAITING,
    ERROR_EMBEDDING_FAILED,
)


async def process_ingestion_job(
    payload: Dict[str, Any],
    progress_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """分发入库任务"""
    if payload.get("type") == "file":
        return await process_file_ingestion_job(payload, progress_callback)
    return await process_text_ingestion_job(payload, progress_callback)


async def process_text_ingestion_job(
    payload: Dict[str, Any],
    progress_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """处理文本入库任务（在 executor 中运行阻塞的嵌入与存储）"""
    title = payload.get("title", "未命名文档")
    content = payload.get("content", "")
    metadata = payload.get("metadata")
    current_user = payload.get("current_user") or {}

    if not content:
        raise ValueError("入库任务缺少内容")

    from app.api.api_v1.endpoints.rag import _do_upload

    loop = asyncio.get_event_loop()

    def _run():
        if progress_callback:
            progress_callback(STAGE_PARSING)
        return _do_upload(title, content, metadata, current_user)

    result = await loop.run_in_executor(None, _run)
    logger.info(f"文本入库完成: {title}")
    return result


async def process_file_ingestion_job(
    payload: Dict[str, Any],
    progress_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """处理文件入库任务（在 executor 中运行阻塞的解析、嵌入与存储）"""
    filename = payload.get("filename", "")
    content_bytes = payload.get("content_bytes", b"")
    document_id = payload.get("document_id")
    current_user = payload.get("current_user") or {}

    loop = asyncio.get_event_loop()

    def _run():
        return _ingest_file_sync(
            filename, content_bytes, document_id, current_user, progress_callback
        )

    result = await loop.run_in_executor(None, _run)
    logger.info(f"文件入库完成: {filename}")
    return result


def _ingest_file_sync(
    filename: str,
    content_bytes: bytes,
    document_id: str,
    current_user: Dict[str, Any],
    progress_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """同步文件入库：写临时文件 → 解析 → 向量化 → 存储 → 清理"""
    from app.api.api_v1.endpoints.rag import get_rag_services
    from app.services.rag.vector_store import VectorRecord
    from app.services.rag.retriever import DocumentChunk as RetrieverChunk
    from app.core.scope import build_upload_scope

    if not content_bytes:
        raise ValueError("入库任务缺少文件内容")

    services = get_rag_services()
    parser = services["parser"]
    embedding = services["embedding"]
    vector_store = services["vector_store"]
    retriever = services["retriever"]

    scope_fields = build_upload_scope(current_user)

    suffix = os.path.splitext(filename)[1].lower() or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content_bytes)
        tmp_path = tmp.name

    try:
        if progress_callback:
            progress_callback(STAGE_PARSING)

        # 解析（异常映射为错误码）
        try:
            doc = parser.parse_file(tmp_path)
        except UnicodeDecodeError as e:
            raise IngestionError(ERROR_TEXT_ENCODING_FAILED, detail=str(e))
        except Exception as e:
            raise IngestionError(ERROR_WORD_PARSE_FAILED, detail=str(e))

        total_chunks = len(doc.chunks)
        now = datetime.now(timezone.utc).isoformat()

        # 扫描件/空文档检测：解析后无文本
        doc_content = getattr(doc, "content", "") or ""
        if not doc_content.strip() or total_chunks == 0:
            if suffix == ".pdf":
                raise IngestionError(ERROR_SCANNED_PDF)
            raise IngestionError(ERROR_WORD_PARSE_FAILED, detail="文档无有效文本")

        if progress_callback:
            progress_callback(STAGE_CHUNKING, {"processed_chunks": 0, "total_chunks": total_chunks})

        records = []
        retriever_chunks = []

        for idx, chunk in enumerate(doc.chunks, 1):
            # 向量化（异常映射为错误码）
            try:
                embed_result = embedding.embed_text(chunk.content)
            except Exception as e:
                if "未初始化" in str(e):
                    raise IngestionError(ERROR_EMBEDDING_WAITING, detail=str(e))
                raise IngestionError(ERROR_EMBEDDING_FAILED, detail=str(e))

            embedding_vector = embed_result.embedding

            payload = {
                "doc_id": document_id,
                "content": chunk.content,
                "title": doc.title,
                "file_name": filename,
                "metadata": chunk.metadata,
                "source": "user_upload",
                "created_at": now,
                **scope_fields,
            }
            records.append(VectorRecord(
                id=chunk.id,
                vector=embedding_vector,
                payload=payload,
            ))
            retriever_chunks.append(RetrieverChunk(
                id=chunk.id,
                doc_id=document_id,
                content=chunk.content,
                embedding=embedding_vector,
                metadata={**chunk.metadata, **scope_fields},
            ))

            if progress_callback:
                progress_callback(STAGE_EMBEDDING, {"processed_chunks": idx, "total_chunks": total_chunks})

        success = vector_store.upsert(records)
        if not success:
            raise RuntimeError("向量存储失败")

        if retriever is not None:
            retriever.add_documents(retriever_chunks)

        return {
            "success": True,
            "document_id": document_id,
            "title": doc.title,
            "file_name": filename,
            "chunks_count": total_chunks,
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
