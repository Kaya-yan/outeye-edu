"""
赛前旧数据清理脚本

备份（Qdrant 向量 + PostgreSQL 文档/块）→ 清理 → 审计。

用法（在 backend 目录下执行）：
    python -m scripts.run_data_migration [备份目录]

默认备份目录为 backups/（脚本会在其下按时间戳生成 JSON 文件）。
"""

import asyncio
import os
import sys


async def _main(backup_dir: str):
    from app.core.database import AsyncSessionLocal
    from app.services.data_migration import DataMigrationService

    service = DataMigrationService()
    async with AsyncSessionLocal() as db:
        result = await service.run_migration(db, backup_dir)

    print("\n===== 数据迁移完成 =====")
    print(f"备份目录: {result['audit']['backup_dir']}")
    print(f"PostgreSQL 备份: {result['backup']['postgres']}")
    print(f"Qdrant 备份: {result['backup']['qdrant']}")
    print(f"PostgreSQL 清理: {result['clear']['postgres']}")
    print(f"Qdrant 清理: {result['clear']['qdrant']}")
    print("=======================\n")
    return result


if __name__ == "__main__":
    backup_dir = sys.argv[1] if len(sys.argv) > 1 else "backups"
    asyncio.run(_main(backup_dir))
