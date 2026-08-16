"""
数据迁移服务

赛前清理旧数据：先备份（Qdrant 向量 + PostgreSQL 文档/块），再清理，并记录审计信息。
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.document import Document, DocumentChunk


class DataMigrationService:
    """数据迁移（清理旧数据）服务"""

    def __init__(self):
        pass

    def _get_vector_store(self):
        """延迟获取向量存储实例（仅向量库，不加载 Embedding 模型）"""
        from urllib.parse import urlparse

        from app.core.config import settings
        from app.services.rag.vector_store import VectorStore

        qdrant_url = getattr(settings, "QDRANT_URL", "http://localhost:6333")
        parsed = urlparse(qdrant_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6333

        return VectorStore(
            host=host,
            port=port,
            collection_name=getattr(settings, "QDRANT_COLLECTION", "outeye_knowledge"),
            vector_size=getattr(settings, "EMBEDDING_DIMENSION", 384),
        )

    async def _backup_postgres(self, db: AsyncSession, backup_path: str) -> dict:
        """备份 PostgreSQL 文档与块到 JSON 文件"""
        docs_result = await db.execute(select(Document))
        documents = docs_result.scalars().all()

        chunks_result = await db.execute(select(DocumentChunk))
        chunks = chunks_result.scalars().all()

        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "documents": [d.to_dict() for d in documents],
            "chunks": [
                {
                    "id": c.id,
                    "document_id": c.document_id,
                    "content": c.content,
                    "chunk_index": c.chunk_index,
                    "vector_id": c.vector_id,
                    "embedding_model": c.embedding_model,
                    "extra_data": c.extra_data,
                }
                for c in chunks
            ],
        }

        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        logger.info(f"PostgreSQL 备份完成: {len(documents)} 文档, {len(chunks)} 块 -> {backup_path}")
        return {"documents_count": len(documents), "chunks_count": len(chunks), "path": backup_path}

    def _backup_qdrant(self, backup_path: str) -> dict:
        """备份 Qdrant 向量到 JSON 文件"""
        vector_store = self._get_vector_store()
        records = vector_store.get_all_records()

        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "collection_name": vector_store.collection_name,
            "records": [
                {
                    "id": r.id,
                    "vector": r.vector,
                    "payload": r.payload,
                }
                for r in records
            ],
        }

        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        logger.info(f"Qdrant 备份完成: {len(records)} 条 -> {backup_path}")
        return {"points_count": len(records), "path": backup_path}

    def _clear_qdrant(self) -> dict:
        """清空 Qdrant 集合中的全部记录"""
        vector_store = self._get_vector_store()
        records = vector_store.get_all_records()
        ids = [r.id for r in records]

        deleted = 0
        if ids:
            vector_store.delete(ids)
            deleted = len(ids)

        logger.info(f"Qdrant 清理完成: 删除 {deleted} 条")
        return {"deleted_points": deleted}

    async def _clear_postgres(self, db: AsyncSession) -> dict:
        """清空 PostgreSQL 文档块与文档"""
        chunks_result = await db.execute(delete(DocumentChunk))
        docs_result = await db.execute(delete(Document))
        await db.commit()

        logger.info(f"PostgreSQL 清理完成: {docs_result.rowcount} 文档, {chunks_result.rowcount} 块")
        return {
            "deleted_documents": docs_result.rowcount,
            "deleted_chunks": chunks_result.rowcount,
        }

    async def run_migration(self, db: AsyncSession, backup_dir: str) -> Dict[str, Any]:
        """
        执行迁移：备份 -> 清理 -> 审计

        Args:
            db: 数据库会话
            backup_dir: 备份目录

        Returns:
            迁移结果（含备份、清理、审计信息）
        """
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        pg_backup_path = os.path.join(backup_dir, f"postgres_{timestamp}.json")
        qdrant_backup_path = os.path.join(backup_dir, f"qdrant_{timestamp}.json")

        logger.info(f"开始数据迁移，备份目录: {backup_dir}")

        # 1. 备份（必须先于清理）
        pg_backup = await self._backup_postgres(db, pg_backup_path)
        qdrant_backup = self._backup_qdrant(qdrant_backup_path)

        # 2. 清理
        qdrant_clear = self._clear_qdrant()
        pg_clear = await self._clear_postgres(db)

        # 3. 审计
        audit = {
            "migrated_at": datetime.now(timezone.utc).isoformat(),
            "backup_dir": backup_dir,
            "postgres_backup_path": pg_backup_path,
            "qdrant_backup_path": qdrant_backup_path,
        }

        result = {
            "backup": {
                "postgres": pg_backup,
                "qdrant": qdrant_backup,
            },
            "clear": {
                "postgres": pg_clear,
                "qdrant": qdrant_clear,
            },
            "audit": audit,
        }

        logger.info(f"数据迁移完成: {result['backup']}, {result['clear']}")
        return result
