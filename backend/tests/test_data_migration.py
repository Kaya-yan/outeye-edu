"""
数据迁移（清理旧数据）测试（TDD）

目标：
1. 清理前必须先备份
2. 备份包含 Qdrant 向量与 PostgreSQL 文档/块
3. 清理后记录审计信息
"""

import json
import os

import pytest
from sqlalchemy import select

from app.models.document import Document, DocumentChunk
from app.services.data_migration import DataMigrationService


class TestDataMigrationService:
    """数据迁移服务测试"""

    @pytest.mark.asyncio
    async def test_backup_before_clear(self, test_db_session, tmp_path, monkeypatch):
        """清理前必须先备份数据"""
        # 准备测试数据
        doc = Document(
            id="doc-1",
            user_id="user-1",
            title="Test Doc",
            file_name="test.pdf",
            file_type="pdf",
            file_size=100,
            content="Hello world",
            status="indexed",
        )
        chunk = DocumentChunk(
            id="chunk-1",
            document_id="doc-1",
            content="Hello world",
            chunk_index=0,
        )
        test_db_session.add(doc)
        test_db_session.add(chunk)
        await test_db_session.commit()

        backup_dir = str(tmp_path / "backup")

        # 用一个假的 Qdrant 备份函数，避免依赖真实 Qdrant
        fake_points = [
            {"id": "qdrant-1", "payload": {"doc_id": "doc-1", "content": "Hello"}}
        ]
        monkeypatch.setattr(
            "app.services.data_migration.DataMigrationService._backup_qdrant",
            lambda self, path: {"points_count": len(fake_points), "path": path},
        )
        monkeypatch.setattr(
            "app.services.data_migration.DataMigrationService._clear_qdrant",
            lambda self: {"deleted_points": 1},
        )

        service = DataMigrationService()
        result = await service.run_migration(test_db_session, backup_dir)

        # 备份文件已生成
        assert result["backup"]["qdrant"]["points_count"] == 1
        assert result["backup"]["postgres"]["documents_count"] == 1

        # 清理后数据库为空
        docs_left = (await test_db_session.execute(select(Document))).scalars().all()
        assert len(docs_left) == 0

        # 审计信息已记录
        assert "audit" in result
        assert result["audit"]["backup_dir"] == backup_dir

    @pytest.mark.asyncio
    async def test_backup_postgres_exports_json(self, test_db_session, tmp_path):
        """PostgreSQL 备份应导出为 JSON 文件"""
        doc = Document(
            id="doc-2",
            user_id="user-1",
            title="Doc 2",
            status="indexed",
        )
        test_db_session.add(doc)
        await test_db_session.commit()

        service = DataMigrationService()
        backup_path = str(tmp_path / "postgres_backup.json")
        result = await service._backup_postgres(test_db_session, backup_path)

        assert result["documents_count"] == 1
        assert os.path.exists(backup_path)

        with open(backup_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["documents"][0]["title"] == "Doc 2"
