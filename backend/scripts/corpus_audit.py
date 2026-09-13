"""
知识库语料质量审计（任务G1 · 只读）

遍历指定 collection 全部 chunk，输出质量分类报告：
- letter_spine  逐字碎行（PDF 提取把字间距误判为换行）
- mid_sentence  半句截断（从句中开始/结束）
- noise_lines   孤立页码 / 页眉页脚形态行
- too_short     过短碎片（<50 字符）
- lang_anomaly  中英文比例异常

用法（在 backend 目录下执行，不写任何数据，可反复跑）：
    PYTHONIOENCODING=utf-8 python scripts/corpus_audit.py
    PYTHONIOENCODING=utf-8 python scripts/corpus_audit.py --collection teaching_knowledge_v2   # 清洗后复检（应接近全绿）
    PYTHONIOENCODING=utf-8 python scripts/corpus_audit.py --samples 20
"""

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    parser = argparse.ArgumentParser(description="知识库语料质量审计（只读）")
    parser.add_argument("--url", default=None, help="Qdrant URL，缺省取 settings.QDRANT_URL")
    parser.add_argument("--collection", default=None, help="collection 名，缺省取 settings.QDRANT_COLLECTION")
    parser.add_argument("--samples", type=int, default=10, help="每类抽样条数")
    args = parser.parse_args()

    from app.core.config import settings
    from app.services.rag.vector_store import VectorStore
    from app.services.rag.corpus_clean import AUDIT_CATEGORIES, audit_chunk

    url = args.url or getattr(settings, "QDRANT_URL", "http://localhost:6333")
    collection = args.collection or getattr(settings, "QDRANT_COLLECTION", "outeye_knowledge")
    parsed = urlparse(url)

    print(f"连接 Qdrant {url} collection={collection} ...")
    store = VectorStore(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6333,
        collection_name=collection,
    )
    records = store.get_all_records()
    if not records:
        print("collection 为空或不可达（backend 为内存降级时也会为空），无数据可审计。")
        return

    total = len(records)
    by_scope = defaultdict(int)
    samples = defaultdict(list)
    counts = defaultdict(int)
    flagged = 0

    for r in records:
        payload = r.payload or {}
        scope = payload.get("scope", "?")
        by_scope[scope] += 1
        issues = audit_chunk(payload.get("content") or "")
        if issues:
            flagged += 1
        for cat in issues:
            counts[cat] += 1
            if len(samples[cat]) < args.samples:
                samples[cat].append(payload.get("content") or "")

    print(f"\n========== 审计报告 ==========")
    print(f"collection: {collection}   backend: {store.backend}")
    print(f"总 chunk 数: {total}   命中问题: {flagged} ({flagged / total * 100:.1f}%)")
    print(f"按 scope: {dict(by_scope)}")
    print("\n各类问题数量与占比：")
    for cat in AUDIT_CATEGORIES:
        n = counts[cat]
        print(f"  {cat:<16} {n:>6}  ({n / total * 100:.1f}%)")
    print("\n各类抽样：")
    for cat in AUDIT_CATEGORIES:
        if not samples[cat]:
            continue
        print(f"\n--- {cat} ×{counts[cat]} ---")
        for i, s in enumerate(samples[cat], 1):
            preview = s.replace("\n", "⏎")[:120]
            print(f"  [{i}] {preview}")

    print("\n提示：清洗后复检命令：")
    print(f"  PYTHONIOENCODING=utf-8 python scripts/corpus_audit.py --collection <新collection>")


if __name__ == "__main__":
    main()
