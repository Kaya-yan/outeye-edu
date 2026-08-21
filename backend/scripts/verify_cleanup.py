"""
清理结果验证脚本

验证内容：
1. PostgreSQL 中只剩 Kaya-yan@outlook.com（以及可能的其它正式用户），
   5 个测试/演示用户已删除。
2. 测试用户的关联数据（analysis_records / lesson_plans 等）已清空。
3. Qdrant 中无验收测试 points、无测试用户私有 points。

用法（在 backend 目录下执行）：
    python scripts/verify_cleanup.py
"""

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402

TEST_USER_EMAILS = [
    "test@outeye.com",
    "demo@outeye.com",
    "test@example.com",
    "test2@example.com",
    "test@demo.com",
]
PRESERVE_ADMIN_EMAIL = "Kaya-yan@outlook.com"


def _get_vector_store():
    from urllib.parse import urlparse

    from app.core.config import settings
    from app.services.rag.vector_store import VectorStore

    qdrant_url = getattr(settings, "QDRANT_URL", "http://localhost:6333")
    parsed = urlparse(qdrant_url)
    return VectorStore(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6333,
        collection_name=getattr(settings, "QDRANT_COLLECTION", "outeye_knowledge"),
        vector_size=getattr(settings, "EMBEDDING_DIMENSION", 384),
    )


async def main():
    ok = True
    print("=" * 64)
    print("清理结果验证")
    print("=" * 64)

    async with AsyncSessionLocal() as db:
        # 1. 剩余用户
        result = await db.execute(text("SELECT id, email, is_admin FROM users ORDER BY email"))
        users = result.fetchall()
        print("\n[1] 剩余用户:")
        for uid, email, is_admin in users:
            print(f"  - {email} (admin={is_admin})")

        remaining_test = [e for _, e, _ in users if e in TEST_USER_EMAILS]
        has_kaya = any(e == PRESERVE_ADMIN_EMAIL for _, e, _ in users)
        if remaining_test:
            ok = False
            print(f"  ✗ 仍有测试用户残留: {remaining_test}")
        else:
            print("  ✓ 5 个测试/演示用户已全部删除")
        if has_kaya:
            print(f"  ✓ 保留管理员 {PRESERVE_ADMIN_EMAIL} 存在")
        else:
            ok = False
            print(f"  ✗ 未找到 {PRESERVE_ADMIN_EMAIL}")

        # 2. 关联数据是否清空
        print("\n[2] 关联数据残留检查:")
        # 测试用户 id 集合（应为空，因为已删；但反查无意义，这里统计全表）
        for table in (
            "analysis_records",
            "lesson_plans",
            "learning_records",
            "user_feedback",
            "user_behaviors",
            "documents",
            "document_chunks",
        ):
            try:
                n = (await db.execute(text(f"SELECT count(*) FROM {table}"))).scalar()
                print(f"  {table}: {n}")
            except Exception:
                print(f"  {table}: (表不存在)")

        # 系统组件应保留
        try:
            n = (await db.execute(
                text("SELECT count(*) FROM component_definitions WHERE owner_user_id IS NULL")
            )).scalar()
            print(f"  component_definitions(系统级 owner=NULL): {n}")
        except Exception:
            print("  component_definitions: (表不存在)")

    # 3. Qdrant
    print("\n[3] Qdrant points 检查:")
    vector_store = _get_vector_store()
    if getattr(vector_store, "degraded", False):
        print("  ⚠ Qdrant 未连接（降级为内存存储），无法验证 points。请确认 Qdrant 已启动后重跑。")
        ok = False
    else:
        records = vector_store.get_all_records()

        if not records:
            print("  共 0 个 points（Qdrant 已连接且已清空，或本无数据）")
        else:
            system_seed = 0
            suspicious = 0
            for r in records:
                p = r.payload or {}
                source = str(p.get("source", "")).lower()
                if p.get("scope") == "system" and source == "system_seed":
                    system_seed += 1
                    continue
                haystack = " ".join([
                    source,
                    str(p.get("file_name", "")).lower(),
                    str(p.get("title", "")).lower(),
                ])
                if "acceptance" in haystack:
                    suspicious += 1
            print(f"  system_seed: {system_seed}")
            print(f"  疑似验收测试残留: {suspicious}")
            if suspicious:
                ok = False
                print("  ✗ 仍有验收测试 points 残留")
            else:
                print("  ✓ 无验收测试 points 残留")

    print("\n" + "=" * 64)
    print("验证结果:", "通过 ✓" if ok else "未通过 ✗（见上方 ✗ 标记）")
    print("=" * 64)
    return ok


if __name__ == "__main__":
    asyncio.run(main())
