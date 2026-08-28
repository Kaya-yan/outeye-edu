"""
教学素材 seed 入库脚本（主入口）

用法：
    # 预览（不入库）
    python scripts/seed_materials.py --batch theory --dry-run

    # 真正入库
    python scripts/seed_materials.py --batch theory --execute

    # 限制只处理前 N 条（测试用）
    python scripts/seed_materials.py --batch theory --dry-run --limit 3

    # interview / lesson 批次（manifest 已生成：manifests/interview.json、lesson.json）
    python scripts/seed_materials.py --batch interview --dry-run
    python scripts/seed_materials.py --batch lesson --execute

约束：
- 不修改现有 5 个 system_seed（Bloom/Krashen 等），新增数据与之并存
- 幂等：按 payload.title 在 system scope 内查重
- 服务器 3.4GB 内存：每 5 篇 GC + sleep 0.3s
- 走 get_rag_services() 拿 embedding/vector_store（不用 IngestionJob 异步队列）
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# 让 seed_lib 可被导入
sys.path.insert(0, str(Path(__file__).resolve().parent))

from seed_lib import (  # noqa: E402
    SeedRecord,
    get_services,
    normalize_file_path,
    seed_batch,
    write_summary,
)

MANIFESTS_DIR = Path(__file__).resolve().parent / "manifests"
RESULTS_DIR = Path(__file__).resolve().parent / "seed_results"

BATCH_CONFIG = {
    "theory": {
        "manifest_file": "theory.json",
        "source_tag": "seed_materials_theory",
        "doc_type": "theory_paper",
        "label": "理论文献",
    },
    "interview": {
        "manifest_file": "interview.json",
        "source_tag": "seed_materials_interview",
        "doc_type": "interview_transcript",
        "label": "访谈记录",
    },
    "lesson": {
        # 2026-08 已执行：24 条 manifest 中 12 条成功（134 chunks 入库 Qdrant）；
        # 12 条 .doc/.txt 因服务器无法解析该格式失败，赛前决策不再补
        "manifest_file": "lesson.json",
        "source_tag": "seed_materials_lesson",
        "doc_type": "lesson_plan",
        "label": "教案案例",
    },
}


def load_manifest(batch: str) -> List[SeedRecord]:
    """从 manifest.json 加载并反序列化为 SeedRecord 列表"""
    cfg = BATCH_CONFIG[batch]
    manifest_path = MANIFESTS_DIR / cfg["manifest_file"]
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"清单文件不存在: {manifest_path}\n"
            f"批次 {batch} 的 manifest 尚未生成，请先运行对应生成器脚本"
        )

    with manifest_path.open(encoding="utf-8") as f:
        manifest = json.load(f)

    entries = manifest.get("entries", [])
    records: List[SeedRecord] = []
    for e in entries:
        # 把 manifest 里的字段映射到 SeedRecord
        # extra_metadata 收集 SeedRecord 未声明的字段（如 interview/lesson 特有字段）
        known_fields = {
            "doc_id", "title", "file_path", "authors", "year", "source",
            "volume", "issue", "pages", "theory_tags", "theory_name",
            "theorist_and_year", "core_content", "application", "abstract",
            "raw_citation",
        }
        # 内部辅助字段（不写入 Qdrant payload）
        internal_fields = {
            "batch", "source_pdf_dir", "raw_entry_index",
            "original_filename", "_pending_verification", "_verification_note",
        }
        # 别名字段：manifest 用的字段名 -> SeedRecord 字段名
        aliases = {
            "source_journal": "source",  # 0729/0811 都用 source_journal
        }

        ctor_kwargs = {}
        extra_metadata = {}
        for k, v in e.items():
            if k in aliases:
                # 把 source_journal 写到 SeedRecord.source，但同时保留在 extra_metadata 供调试
                ctor_kwargs[aliases[k]] = v
                extra_metadata[k] = v
            elif k in known_fields:
                ctor_kwargs[k] = v
            elif k in internal_fields:
                extra_metadata[f"_{k}"] = v
            else:
                # interview/lesson 特有字段
                extra_metadata[k] = v

        # 把 original_filename 也写入 metadata，方便后续溯源
        if "original_filename" in e:
            extra_metadata.setdefault("original_filename", e["original_filename"])
        if "_pending_verification" in e:
            extra_metadata.setdefault("_pending_verification", e["_pending_verification"])
        if "_verification_note" in e:
            extra_metadata.setdefault("_verification_note", e["_verification_note"])

        # 运行时路径映射：把 manifest 里的本地 Windows 路径映射为服务器路径。
        # 本地开发机上路径已存在、原样返回；服务器上不存在则映射到 /opt/outeye-edu/seed-materials/
        if "file_path" in ctor_kwargs:
            ctor_kwargs["file_path"] = normalize_file_path(ctor_kwargs["file_path"])

        ctor_kwargs["extra_metadata"] = extra_metadata
        records.append(SeedRecord(**ctor_kwargs))

    return records


def run_batch(batch: str, dry_run: bool, execute: bool, limit: Optional[int]) -> int:
    """运行指定批次，返回 exit code（0=成功，1=有失败）"""
    if not dry_run and not execute:
        print("错误：必须指定 --dry-run 或 --execute 之一", file=sys.stderr)
        return 2

    cfg = BATCH_CONFIG[batch]
    print(f"\n=== 批次：{cfg['label']}（{batch}）===")
    print(f"source_tag: {cfg['source_tag']}")
    print(f"doc_type:   {cfg['doc_type']}")
    print(f"模式:       {'dry-run（预览不入库）' if dry_run else 'execute（真正入库）'}")
    if limit:
        print(f"limit:      前 {limit} 条")

    # 加载 manifest
    try:
        records = load_manifest(batch)
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2
    print(f"已加载 {len(records)} 条记录")

    # 校验文件存在性（前置检查，file_path 已在 load_manifest 时做过路径映射）
    missing = [r for r in records if not Path(r.file_path).exists()]
    if missing:
        print(f"\n警告：{len(missing)} 个文件不存在，将跳过：", file=sys.stderr)
        for r in missing[:5]:
            print(
                f"  - {r.doc_id} 文件不存在（路径已映射为：{r.file_path}），"
                f"请确认素材已传到服务器",
                file=sys.stderr,
            )
        if len(missing) > 5:
            print(f"  ... 共 {len(missing)} 个", file=sys.stderr)

    # 加载 RAG 服务
    print("\n加载 RAG 服务（首次需加载 Embedding 模型，约 60 秒）...")
    parser, embedding, vector_store = get_services()
    print("RAG 服务已就绪")

    # 执行批次
    print()
    results, failures = seed_batch(
        parser, embedding, vector_store,
        records=records,
        source_tag=cfg["source_tag"],
        doc_type=cfg["doc_type"],
        dry_run=dry_run,
        limit=limit,
    )

    # 摘要
    success_count = sum(1 for r in results if r.success and not r.skipped)
    skipped_count = sum(1 for r in results if r.skipped)
    failed_count = len(failures)
    total_chunks = sum(r.chunks_written for r in results if not r.skipped)

    print()
    print("=== 摘要 ===")
    print(f"总数:        {len(results)}")
    print(f"成功入库:    {success_count}")
    print(f"幂等跳过:    {skipped_count}")
    print(f"失败:        {failed_count}")
    print(f"总 chunks:   {total_chunks}")

    # 写入结果 JSON
    summary_path = write_summary(results, failures, batch, RESULTS_DIR)
    print(f"\n结果已保存: {summary_path}")

    return 0 if failed_count == 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description="教学素材 seed 入库脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 预览 theory 批次（不入库）
  python scripts/seed_materials.py --batch theory --dry-run

  # 真正入库 theory 批次
  python scripts/seed_materials.py --batch theory --execute

  # 限制前 3 条做测试
  python scripts/seed_materials.py --batch theory --execute --limit 3

  # interview / lesson 批次（需先实现对应 manifest）
  python scripts/seed_materials.py --batch interview --dry-run
""",
    )
    parser.add_argument(
        "--batch",
        choices=["theory", "interview", "lesson", "all"],
        required=True,
        help="批次名称（all = 依次执行 theory/interview/lesson）",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="预览不入库")
    group.add_argument("--execute", action="store_true", help="真正入库")
    parser.add_argument("--limit", type=int, default=None, help="限制处理条数（测试用）")

    args = parser.parse_args()

    if args.batch == "all":
        # 依次执行三个批次
        exit_codes = []
        for b in ["theory", "interview", "lesson"]:
            try:
                code = run_batch(b, args.dry_run, args.execute, args.limit)
                exit_codes.append(code)
            except FileNotFoundError as e:
                # interview/lesson manifest 未实现时跳过
                print(f"跳过批次 {b}: {e}", file=sys.stderr)
                exit_codes.append(2)
        # 任一非 0 即视为失败
        sys.exit(0 if all(c == 0 for c in exit_codes) else 1)
    else:
        sys.exit(run_batch(args.batch, args.dry_run, args.execute, args.limit))


if __name__ == "__main__":
    main()
