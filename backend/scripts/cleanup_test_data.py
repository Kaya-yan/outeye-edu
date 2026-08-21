"""
赛前测试数据清理脚本（最终版：数据库 + Qdrant，纯 SQL 实现）

删除对象：
1. PostgreSQL 中 5 个测试/演示用户及其全部关联数据（按外键依赖顺序）。
2. Qdrant 中验收测试 points（source/file_name/title 含 acceptance）以及
   这些测试用户拥有的私有 points。

保留对象（绝不删除）：
- Kaya-yan@outlook.com 用户及其所有数据
- system_seed 知识（scope=system, source=system_seed）
- component_definitions 中 owner_user_id=None 的系统级组件
- 其它 scope=system 的非验收测试数据

说明：本脚本全部使用原生 SQL，不依赖 ORM 模型列，避免模型与数据库
schema 漂移（如 user_feedback.sentiment 尚未迁移）导致的报错。

用法（在 backend 目录下执行）：
    # 试运行：只打印将删除的内容，不做任何改动
    python scripts/cleanup_test_data.py

    # 真正执行：先备份到 backups/cleanup_<时间戳>/，再删除
    python scripts/cleanup_test_data.py --execute
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# 服务器无法访问 huggingface.co，强制离线模式（本脚本不加载 Embedding 模型，保险起见）
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# 让脚本可直接执行，无需手动设置 PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402

# 待清理的测试/演示用户（删除全部）与需保留的管理员
TEST_USER_EMAILS = [
    "test@outeye.com",
    "demo@outeye.com",
    "test@example.com",
    "test2@example.com",
    "test@demo.com",
]
PRESERVE_ADMIN_EMAIL = "Kaya-yan@outlook.com"


def _in_clause(col: str, values: list) -> tuple:
    """构造参数化 IN 子句，返回 (子句字符串, 参数字典)。"""
    placeholders = ",".join(f":v{i}" for i in range(len(values)))
    params = {f"v{i}": v for i, v in enumerate(values)}
    return f"{col} IN ({placeholders})", params


async def _query_rows(db, table: str, col: str, values: list) -> list:
    """按列值查询并返回行（dict 列表）；表不存在时返回空。"""
    if not values:
        return []
    clause, params = _in_clause(col, values)
    try:
        result = await db.execute(text(f"SELECT * FROM {table} WHERE {clause}"), params)
        return [dict(r._mapping) for r in result.fetchall()]
    except Exception:
        await db.rollback()
        return []


async def _query_ids(db, table: str, id_col: str, col: str, values: list) -> list:
    """查询某表的 id 列（用于父表删除前反查子表）。"""
    if not values:
        return []
    clause, params = _in_clause(col, values)
    try:
        result = await db.execute(
            text(f"SELECT {id_col} FROM {table} WHERE {clause}"), params
        )
        return [r[0] for r in result.fetchall()]
    except Exception:
        await db.rollback()
        return []


async def _delete_rows(db, table: str, col: str, values: list) -> int:
    """按列值删除行，返回删除行数；表不存在时返回 0。"""
    if not values:
        return 0
    clause, params = _in_clause(col, values)
    try:
        result = await db.execute(text(f"DELETE FROM {table} WHERE {clause}"), params)
        return result.rowcount or 0
    except Exception:
        await db.rollback()
        return 0


async def _collect_backup(db, test_user_ids: list) -> dict:
    """收集全部待删数据（备份 + 统计），返回 {table: [rows]}。"""
    data = {}

    # 直接以 user_id 关联的表
    for table in (
        "analysis_records",
        "lesson_plans",
        "learning_records",
        "user_feedback",
        "user_behaviors",
    ):
        data[table] = await _query_rows(db, table, "user_id", test_user_ids)

    # 以 owner_user_id 关联的表（保留 owner=None 的系统级组件）
    for table in ("courseware_projects", "component_definitions"):
        data[table] = await _query_rows(db, table, "owner_user_id", test_user_ids)

    # 课件子表（通过 project_id 反查）
    project_ids = await _query_ids(
        db, "courseware_projects", "id", "owner_user_id", test_user_ids
    )
    for table in ("export_artifacts", "presentation_profiles", "courseware_versions"):
        data[table] = await _query_rows(db, table, "project_id", project_ids)

    # 文档与块（通过 document_id 反查）
    data["documents"] = await _query_rows(db, "documents", "user_id", test_user_ids)
    doc_ids = await _query_ids(db, "documents", "id", "user_id", test_user_ids)
    data["document_chunks"] = await _query_rows(db, "document_chunks", "document_id", doc_ids)

    # 专家评审（plan_id 是普通字符串，无真实外键，且表可能不存在）
    plan_ids = await _query_ids(db, "lesson_plans", "id", "user_id", test_user_ids)
    data["expert_reviews"] = await _query_rows(db, "expert_reviews", "plan_id", plan_ids)

    # 用户本身
    data["users"] = await _query_rows(db, "users", "id", test_user_ids)

    return data


async def _delete_all(db, test_user_ids: list) -> dict:
    """按外键依赖顺序删除全部测试用户的数据，返回 {table: 删除行数}。"""
    counts = {}

    # 1) 课件子表 → 课件项目
    project_ids = await _query_ids(
        db, "courseware_projects", "id", "owner_user_id", test_user_ids
    )
    for table in ("export_artifacts", "presentation_profiles", "courseware_versions"):
        counts[table] = await _delete_rows(db, table, "project_id", project_ids)
    counts["courseware_projects"] = await _delete_rows(
        db, "courseware_projects", "owner_user_id", test_user_ids
    )

    # 2) 组件定义（仅删除测试用户拥有的，owner=NULL 系统组件不动）
    counts["component_definitions"] = await _delete_rows(
        db, "component_definitions", "owner_user_id", test_user_ids
    )

    # 3) 文档块 → 文档
    doc_ids = await _query_ids(db, "documents", "id", "user_id", test_user_ids)
    counts["document_chunks"] = await _delete_rows(
        db, "document_chunks", "document_id", doc_ids
    )
    counts["documents"] = await _delete_rows(db, "documents", "user_id", test_user_ids)

    # 4) 专家评审（先于教案删除；表可能不存在）
    plan_ids = await _query_ids(db, "lesson_plans", "id", "user_id", test_user_ids)
    counts["expert_reviews"] = await _delete_rows(db, "expert_reviews", "plan_id", plan_ids)

    # 5) 教案 → 分析记录（教案有 analysis_id 外键，须先删教案）
    counts["lesson_plans"] = await _delete_rows(db, "lesson_plans", "user_id", test_user_ids)
    counts["analysis_records"] = await _delete_rows(
        db, "analysis_records", "user_id", test_user_ids
    )

    # 6) 学习记录 / 反馈 / 行为
    counts["learning_records"] = await _delete_rows(
        db, "learning_records", "user_id", test_user_ids
    )
    counts["user_feedback"] = await _delete_rows(db, "user_feedback", "user_id", test_user_ids)
    counts["user_behaviors"] = await _delete_rows(
        db, "user_behaviors", "user_id", test_user_ids
    )

    # 7) 用户本身
    counts["users"] = await _delete_rows(db, "users", "id", test_user_ids)

    await db.commit()
    return counts


def _get_vector_store():
    """获取向量库实例（不加载 Embedding 模型）"""
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


def _classify_qdrant_point(payload: dict, test_user_ids: set, kaya_id):
    """分类一个 Qdrant point：返回 (是否删除, 分类标签)。"""
    scope = payload.get("scope")
    source = str(payload.get("source", "")).lower()
    owner_id = payload.get("owner_id")

    # 保留 system_seed（永久保留）
    if scope == "system" and source == "system_seed":
        return False, "preserved:system_seed"

    # 保留 Kaya-yan 管理员数据
    if kaya_id and owner_id == kaya_id:
        return False, "preserved:kaya_admin"

    # 删除验收测试数据（source / file_name / title 含 acceptance）
    haystack = " ".join([
        source,
        str(payload.get("file_name", "")).lower(),
        str(payload.get("title", "")).lower(),
    ])
    if "acceptance" in haystack:
        return True, "acceptance_test"

    # 删除测试用户的私有数据
    if owner_id in test_user_ids:
        return True, "test_user_private"

    return False, "preserved:other"


def _backup(db_data: dict, qdrant_points: list, backup_dir: str) -> str:
    """将待删除数据备份为 JSON 文件，返回 PostgreSQL 备份文件路径。"""
    os.makedirs(backup_dir, exist_ok=True)
    pg_path = os.path.join(backup_dir, "postgres_affected.json")
    qdrant_path = os.path.join(backup_dir, "qdrant_affected.json")

    pg_payload = {"exported_at": datetime.now(timezone.utc).isoformat(), "data": db_data}
    with open(pg_path, "w", encoding="utf-8") as f:
        json.dump(pg_payload, f, ensure_ascii=False, indent=2, default=str)

    qdrant_payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "records": [
            {"id": r.id, "vector": r.vector, "payload": r.payload} for r in qdrant_points
        ],
    }
    with open(qdrant_path, "w", encoding="utf-8") as f:
        json.dump(qdrant_payload, f, ensure_ascii=False, indent=2, default=str)

    return pg_path


async def main(execute: bool):
    print("=" * 64)
    print("赛前测试数据清理（最终版：数据库 + Qdrant）")
    print("模式:", "【真正执行】" if execute else "【试运行 dry-run】")
    print("=" * 64)

    async with AsyncSessionLocal() as db:
        # 1. 定位用户（纯 SQL）
        clause, params = _in_clause("email", TEST_USER_EMAILS)
        test_users = (
            await db.execute(
                text(f"SELECT id, email FROM users WHERE {clause} ORDER BY email"), params
            )
        ).fetchall()
        test_user_ids = [r[0] for r in test_users]
        test_user_ids_set = set(test_user_ids)

        kaya = (
            await db.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": PRESERVE_ADMIN_EMAIL},
            )
        ).fetchone()
        kaya_id = kaya[0] if kaya else None

        print("\n[PostgreSQL] 待删除测试用户:")
        for r in test_users:
            print(f"  - {r[1]} (id={r[0]})")
        if not test_users:
            print("  （未找到任何测试用户）")
        if kaya_id:
            print(f"[PostgreSQL] 保留管理员: {PRESERVE_ADMIN_EMAIL} (id={kaya_id})")
        else:
            print(f"[PostgreSQL] 警告: 未找到 {PRESERVE_ADMIN_EMAIL}")

        # 2. 收集待删数据（备份 + 统计）
        db_data = await _collect_backup(db, test_user_ids) if test_user_ids else {}

        # 3. 扫描 Qdrant
        print("\n[Qdrant] 扫描 points ...")
        vector_store = _get_vector_store()
        records = vector_store.get_all_records()

        to_delete = []
        categories = {}
        preserved = {"system_seed": 0, "kaya_admin": 0, "other": 0}
        for r in records:
            do_delete, label = _classify_qdrant_point(r.payload or {}, test_user_ids_set, kaya_id)
            if do_delete:
                to_delete.append(r)
                categories[label] = categories.get(label, 0) + 1
            else:
                key = label.split(":")[-1]
                preserved[key] = preserved.get(key, 0) + 1

        # 4. 统计 PG 待删行数
        print("\n--- 待删除 PostgreSQL 行数（按表）---")
        pg_total = 0
        for table, rows in db_data.items():
            n = len(rows)
            pg_total += n
            if n:
                print(f"  {table}: {n}")
        if pg_total == 0:
            print("  （无）")

        # 5. 统计 Qdrant 待删
        print("\n--- 待删除 Qdrant points ---")
        for label, n in sorted(categories.items()):
            print(f"  {label}: {n}")
        print(f"  合计: {len(to_delete)}")
        print("\n--- 保留 Qdrant points ---")
        for label, n in sorted(preserved.items()):
            print(f"  {label}: {n}")

        if not execute:
            print("\n[试运行] 未做任何改动。确认无误后加 --execute 真正执行。")
            return

        # 6. 备份
        print("\n开始备份 ...")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join("backups", f"cleanup_{timestamp}")
        pg_backup = _backup(db_data, to_delete, backup_dir)
        print(f"  备份目录: {backup_dir}")
        print(f"  PostgreSQL 备份: {pg_backup}")
        print(f"  Qdrant 备份: {os.path.join(backup_dir, 'qdrant_affected.json')}")

        # 7. 删除（先 PG，后 Qdrant）
        print("\n开始删除 ...")
        pg_counts = await _delete_all(db, test_user_ids) if test_user_ids else {}

        qdrant_deleted = 0
        if to_delete:
            vector_store.delete([r.id for r in to_delete])
            qdrant_deleted = len(to_delete)

        # 8. 审计报告
        print("\n" + "=" * 64)
        print("审计报告")
        print("=" * 64)
        print(f"执行时间: {datetime.now(timezone.utc).isoformat()}")
        print(f"备份目录: {backup_dir}")
        print("\n[PostgreSQL 删除]")
        pg_deleted_total = 0
        for table, n in pg_counts.items():
            pg_deleted_total += n
            print(f"  {table}: {n}")
        print(f"  实际删除行数: {pg_deleted_total}")
        print("\n[Qdrant 删除]")
        for label, n in sorted(categories.items()):
            print(f"  {label}: {n}")
        print(f"  实际删除 points: {qdrant_deleted}")
        print("\n清理完成。")


if __name__ == "__main__":
    execute = "--execute" in sys.argv
    asyncio.run(main(execute=execute))
