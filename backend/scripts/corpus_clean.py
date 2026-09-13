"""
知识库语料清洗与重建（任务G1）

流程：读源 collection → 按文档聚合 → 逐字碎行合并 → 规范化（NFKC/零宽/页码页脚）
→ 句边界重切（200-800 字符、重叠 1 句、不切句）→ 质量过滤（不合格 quarantine 不入库）
→ 重新 embedding → 灌入新 collection（缺省 teaching_knowledge_v2）。

- 旧 collection 一律不动，回滚 = 应用环境变量换回旧名重启；
- scope=private 的用户文档原样搬运（保留原向量），切库不丢个人资料；
- --llm-repair 对「英文逐字黏连」的隔离块用现有 LLM 通道整理成通顺段落，
  成功入库并标 payload.cleaned_by_llm=true；
- --dry-run 只打印前后对照，不写任何数据。

用法（在 backend 目录下执行）：
    PYTHONIOENCODING=utf-8 python scripts/corpus_clean.py --dry-run          # 先看对照
    PYTHONIOENCODING=utf-8 python scripts/corpus_clean.py                    # 正式清洗
    PYTHONIOENCODING=utf-8 python scripts/corpus_clean.py --llm-repair       # 含 LLM 修复
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_TARGET = "teaching_knowledge_v2"

LLM_REPAIR_SYSTEM = (
    "你是语料修复员。输入是 PDF 提取时逐字母竖排、合并后黏成串的破损英文片段。"
    "请仅恢复单词间的空格与标点，整理成通顺段落；不得增删含义、不得翻译、不得添加解释。"
    "直接输出修复后的段落文本，不要任何前后缀。"
)


def llm_repair(generator, text: str) -> str:
    answer, _usage = generator._generate_with_api([
        {"role": "system", "content": LLM_REPAIR_SYSTEM},
        {"role": "user", "content": text[:2000]},
    ])
    return (answer or "").strip()


def main():
    parser = argparse.ArgumentParser(description="知识库语料清洗与重建")
    parser.add_argument("--url", default=None, help="Qdrant URL，缺省取 settings.QDRANT_URL")
    parser.add_argument("--source", default=None, help="源 collection，缺省取 settings.QDRANT_COLLECTION")
    parser.add_argument("--target", default=DEFAULT_TARGET, help=f"目标 collection，缺省 {DEFAULT_TARGET}")
    parser.add_argument("--dry-run", action="store_true", help="只打印对照与统计，不写入")
    parser.add_argument("--llm-repair", action="store_true", help="对英文黏连隔离块走 LLM 修复")
    parser.add_argument("--sample", type=int, default=20, help="打印前后对照条数")
    parser.add_argument("--quarantine-file", default=None, help="隔离块清单 JSON 输出路径")
    args = parser.parse_args()

    from app.core.config import settings
    from app.core.scope import SCOPE_SYSTEM
    from app.services.rag.vector_store import VectorStore, VectorRecord
    from app.services.rag.embedding import EmbeddingService
    from app.services.rag.corpus_clean import chunk_quality, clean_document

    url = args.url or getattr(settings, "QDRANT_URL", "http://localhost:6333")
    source = args.source or getattr(settings, "QDRANT_COLLECTION", "outeye_knowledge")
    parsed = urlparse(url)

    print(f"连接 Qdrant {url}   源={source} → 目标={args.target}   dry_run={args.dry_run}")
    src_store = VectorStore(host=parsed.hostname or "localhost", port=parsed.port or 6333,
                            collection_name=source)
    records = src_store.get_all_records()
    if not records:
        print("源 collection 为空或不可达，终止。")
        return

    # 按文档聚合
    docs = defaultdict(list)
    private_records = []
    for r in records:
        p = r.payload or {}
        if p.get("scope") == SCOPE_SYSTEM:
            docs[p.get("doc_id") or f"unknown-{r.id}"].append(p)
        else:
            private_records.append(r)

    print(f"共 {len(records)} 条：system 文档 {len(docs)} 个 / private 记录 {len(private_records)} 条")

    # 清洗 system 文档
    generator = None
    if args.llm_repair:
        from app.services.rag import RAGGenerator
        generator = RAGGenerator(
            api_key=getattr(settings, "LLM_API_KEY", None),
            api_base=getattr(settings, "LLM_BASE_URL", None),
            model=getattr(settings, "LLM_MODEL", "deepseek-chat"),
        )

    all_chunks = []          # [(doc_id, payload_base, content, cleaned_by_llm)]
    quarantine = []          # [{"doc_id", "reason", "content"}]
    pairs = []               # 前后对照样本
    for doc_id, chunks in docs.items():
        base = {k: chunks[0].get(k) for k in
                ("title", "scope", "owner_id", "source", "doc_type", "tags", "created_at")}
        before = max(((c.get("content") or "").strip() for c in chunks), key=len, default="")
        clean, quarantined = clean_document(chunks)
        repaired_flags = []
        if generator:
            still = []
            for piece, reason in quarantined:
                if reason == "glued_needs_llm":
                    try:
                        fixed = llm_repair(generator, piece)
                        ok, why = chunk_quality(fixed, had_glue=True)
                        if fixed and ok:
                            clean.append(fixed)
                            repaired_flags.append(len(clean) - 1)
                            continue
                    except Exception as e:
                        print(f"  [warn] LLM 修复失败 ({doc_id}): {type(e).__name__}: {e}")
                still.append((piece, reason))
            quarantined = still
        for i, content in enumerate(clean):
            all_chunks.append((doc_id, base, content, i in repaired_flags))
        for piece, reason in quarantined:
            quarantine.append({"doc_id": doc_id, "reason": reason, "content": piece[:400]})
        if clean and args.sample and len(pairs) < args.sample and before != clean[0]:
            pairs.append((doc_id, before, clean[0]))

    # embedding + 灌库
    if args.dry_run:
        print(f"\n[dry-run] 清洗后 system chunk 数: {len(all_chunks)}   隔离: {len(quarantine)}   "
              f"private 原样搬运: {len(private_records)}")
    else:
        print(f"\n加载 Embedding 模型并生成向量（system {len(all_chunks)} 条）...")
        embedding = EmbeddingService(
            model_name=getattr(settings, "EMBEDDING_MODEL",
                               "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
            api_key=getattr(settings, "LLM_API_KEY", None),
            api_base=getattr(settings, "LLM_BASE_URL", None),
        )
        texts = [c[2] for c in all_chunks]
        vectors = [res.embedding for res in embedding.embed_batch(texts)]
        dim = len(vectors[0]) if vectors else 384
        dst_store = VectorStore(host=parsed.hostname or "localhost", port=parsed.port or 6333,
                                collection_name=args.target, vector_size=dim)

        points = []
        for (doc_id, base, content, by_llm), vec in zip(all_chunks, vectors):
            payload = dict(base)
            payload.update({"doc_id": doc_id, "chunk_index": 0, "content": content})
            if by_llm:
                payload["cleaned_by_llm"] = True
            points.append(VectorRecord(id=f"{doc_id}:c{len(points):04d}", vector=vec, payload=payload))
        # 修正 chunk_index（构建时逐文档计数）
        idx = defaultdict(int)
        for p in points:
            p.payload["chunk_index"] = idx[p.payload["doc_id"]]
            idx[p.payload["doc_id"]] += 1
        if private_records:
            points.extend(VectorRecord(id=r.id, vector=r.vector or [], payload=dict(r.payload or {}))
                          for r in private_records)

        BATCH = 128
        t0 = time.time()
        for i in range(0, len(points), BATCH):
            ok = dst_store.upsert(points[i:i + BATCH])
            if not ok:
                print(f"[error] 批次 {i // BATCH} 写入失败，终止。")
                return
        print(f"已写入 {len(points)} 条 → {args.target}（耗时 {time.time() - t0:.1f}s）")

    # 隔离清单
    if args.quarantine_file and quarantine:
        Path(args.quarantine_file).write_text(
            json.dumps(quarantine, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"隔离清单已写 {args.quarantine_file}")

    # 前后对照
    if pairs:
        print(f"\n========== 清洗前后对照（{len(pairs)} 条抽样） ==========")
        for i, (doc_id, before, after) in enumerate(pairs, 1):
            print(f"\n[{i}] doc={doc_id}")
            print(f"  前: {before[:100]!r}")
            print(f"  后: {after[:100]!r}")
    if quarantine:
        from collections import Counter
        print(f"\n隔离块原因分布: {dict(Counter(q['reason'] for q in quarantine))}")

    print("\n后续步骤：")
    print(f"  1) 复检: PYTHONIOENCODING=utf-8 python scripts/corpus_audit.py --collection {args.target}")
    print(f"  2) 抽样检索确认可读后，服务器 .env 将 QDRANT_COLLECTION={args.target} 并重启后端")
    print(f"  3) 回滚: QDRANT_COLLECTION 改回 {source} 重启即可（旧库未动）")


if __name__ == "__main__":
    main()
