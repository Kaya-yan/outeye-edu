"""
seed 脚本共用工具库

提供：
- get_services() 拉取 RAG 服务（parser, embedding, vector_store）
- chunk_by_paragraph() 按自然段落分块（不依赖 DocumentParser._chunk_text 的固定字符数逻辑）
- seed_batch() 批量处理：解析 -> 分块 -> 向量化 -> 入库
- 幂等：按 payload.title 在 system scope 内查重
- 内存控制：每 N 篇 GC + sleep，避免 3.4GB 服务器 OOM
"""

import gc
import json
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 服务器无法访问 huggingface.co，强制离线模式（参照 reseed_knowledge.py:20-21）
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# 让脚本可直接执行，无需手动设置 PYTHONPATH
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))


# --- 常量 ---
SCOPE_SYSTEM = "system"
SCOPE_PRIVATE = "private"

CHUNK_SIZE_LIMIT = 512
CHUNK_SIZE_MIN = 100
GC_EVERY_N_DOCS = 5
GC_SLEEP_SECONDS = 0.3

# 现有 5 个 system_seed 的 source 标记为 "system_seed"
# seed_materials 新数据用 "seed_materials_theory/interview/lesson" 区分
EXISTING_SYSTEM_SOURCE_TAG = "system_seed"


@dataclass
class SeedRecord:
    """单条 seed 数据条目（从 manifest.json 反序列化）"""
    doc_id: str
    file_path: str
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    source: Optional[str] = None          # 期刊/出版社
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    theory_tags: List[str] = field(default_factory=list)
    theory_name: Optional[str] = None
    theorist_and_year: Optional[str] = None
    core_content: Optional[str] = None
    application: Optional[str] = None
    abstract: Optional[str] = None
    raw_citation: Optional[str] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SeedResult:
    """单条 seed 处理结果"""
    doc_id: str
    title: str
    file_path: str
    success: bool
    skipped: bool = False
    chunks_written: int = 0
    error: Optional[str] = None


def get_services():
    """拉取 RAG 服务（含 Embedding 模型，约需 60 秒首次加载）

    返回 (parser, embedding, vector_store)
    """
    from app.api.api_v1.endpoints.rag import get_rag_services
    services = get_rag_services()
    return services["parser"], services["embedding"], services["vector_store"]


def normalize_file_path(file_path: str) -> str:
    """把本地 Windows 绝对路径映射为服务器路径（幂等）

    场景：manifest 里的 file_path 记录的是本地 Windows 路径
    （如 C:\\Users\\ht\\...\\seed-materials\\...），服务器上这些文件不存在，
    需要映射到 /opt/outeye-edu/seed-materials/<相对路径>。

    逻辑：
    1. 若路径本机已存在，原样返回（本地开发机上 manifest 路径直接可用）
    2. 若为 Windows 绝对路径（盘符开头）且本机不存在，映射到服务器
       seed-materials 根下的相对路径
    3. 其余情况原样返回

    只做运行时映射，不改动 manifest JSON 本身。
    """
    if not file_path:
        return file_path

    # 本机已存在则直接返回，保证本地开发机不受映射影响
    if Path(file_path).exists():
        return file_path

    # 统一为 forward slash，便于切分相对路径
    norm = file_path.replace("\\", "/")

    # Windows 绝对路径（C:/ 或 C:\ 等盘符开头）
    if re.match(r"^[A-Za-z]:/", norm):
        if "seed-materials" in norm:
            relative = norm.split("seed-materials", 1)[1].lstrip("/")
            return f"/opt/outeye-edu/seed-materials/{relative}"
        # 兜底：只保留文件名，放到 seed-materials 根下
        return f"/opt/outeye-edu/seed-materials/{Path(norm).name}"

    return file_path


def parse_file_to_text(parser, file_path: str) -> Tuple[str, Dict[str, Any]]:
    """解析文件，返回 (全文文本, 文件元数据)

    直接调用 parser._parse_pdf / _parse_docx / _parse_text 内部方法，
    不走 parse_file（后者会自动按固定字符数分块，与 seed 段落分块策略冲突）。
    """
    file_path = normalize_file_path(file_path)
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parser._parse_pdf(path)
    if suffix in (".docx", ".doc"):
        return parser._parse_docx(path)
    if suffix == ".txt":
        return parser._parse_text(path)
    if suffix == ".md":
        return parser._parse_markdown(path)
    if suffix in (".html", ".htm"):
        return parser._parse_html(path)
    raise ValueError(f"不支持的文件格式: {suffix}")


def chunk_by_paragraph(
    text: str,
    doc_id: str,
    size_limit: int = CHUNK_SIZE_LIMIT,
    min_size: int = CHUNK_SIZE_MIN,
) -> List[Dict[str, Any]]:
    """按自然段落分块

    策略：
    1. 按双换行切段落
    2. 短段落（< min_size）合并到相邻段落
    3. 长段落（> size_limit）按句子边界切分
    """
    if not text or not text.strip():
        return []

    raw_paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]
    if not paragraphs:
        return []

    # 合并短段落：buffer 累积，超限就 flush
    merged: List[str] = []
    buffer = ""
    for p in paragraphs:
        if len(buffer) + len(p) + 1 <= size_limit:
            buffer = (buffer + "\n" + p).strip() if buffer else p
        else:
            if buffer:
                merged.append(buffer)
            buffer = p
    if buffer:
        merged.append(buffer)

    # 切分超长段落 + 生成最终 chunks
    chunks: List[Dict[str, Any]] = []
    chunk_index = 0
    for para in merged:
        if len(para) <= size_limit:
            if len(para) >= min_size or len(merged) == 1:
                chunks.append({
                    "content": para,
                    "chunk_index": chunk_index,
                    "chunk_id": f"{doc_id}_c{chunk_index:03d}",
                })
                chunk_index += 1
            continue
        # 超长段落按句子边界切分
        for sub in _split_long_paragraph(para, size_limit, min_size):
            chunks.append({
                "content": sub,
                "chunk_index": chunk_index,
                "chunk_id": f"{doc_id}_c{chunk_index:03d}",
            })
            chunk_index += 1
    return chunks


def _split_long_paragraph(text: str, size_limit: int, min_size: int) -> List[str]:
    """按句子边界切分超长段落（支持中英文句号、问号、感叹号）"""
    sentence_ends = "。？！？！.?!"
    chunks: List[str] = []
    buffer = ""
    i = 0
    while i < len(text):
        next_end = -1
        upper = min(i + size_limit, len(text))
        for j in range(i + min_size, upper):
            if text[j] in sentence_ends:
                next_end = j + 1
                break
        if next_end == -1:
            next_end = upper

        sentence = text[i:next_end]
        if len(buffer) + len(sentence) <= size_limit:
            buffer += sentence
        else:
            if len(buffer) >= min_size:
                chunks.append(buffer)
            buffer = sentence
        i = next_end

    if buffer and len(buffer) >= min_size:
        chunks.append(buffer)
    return chunks


def resolve_title(record: SeedRecord) -> str:
    """返回记录的有效展示标题（幂等、非空）

    theory 清单有显式 title；interview/lesson 清单无 title 字段，
    从 extra_metadata 派生：
    - interview: interview_topic / topic
    - lesson: course + unit / course
    - 兜底: original_filename / doc_id
    """
    if record.title:
        return record.title
    meta = record.extra_metadata or {}
    topic = meta.get("interview_topic") or meta.get("topic")
    if topic:
        return topic
    course = meta.get("course")
    unit = meta.get("unit")
    if course:
        return f"{course} {unit}".strip() if unit else course
    return meta.get("original_filename") or record.doc_id


def build_payload(
    record: SeedRecord,
    chunk: Dict[str, Any],
    source_tag: str,
    doc_type: str,
) -> Dict[str, Any]:
    """构造 Qdrant payload（参照 knowledge_seed.py:97-108 字段集）"""
    return {
        "doc_id": record.doc_id,
        "title": resolve_title(record),
        "content": chunk["content"],
        "metadata": {
            "authors": record.authors,
            "year": record.year,
            "source": record.source,
            "volume": record.volume,
            "issue": record.issue,
            "pages": record.pages,
            "theory_tags": record.theory_tags,
            "theory_name": record.theory_name,
            "theorist_and_year": record.theorist_and_year,
            "core_content": record.core_content,
            "application": record.application,
            "abstract": record.abstract,
            "raw_citation": record.raw_citation,
            "file_path": record.file_path,
            "chunk_index": chunk["chunk_index"],
            "original_filename": Path(record.file_path).name,
            **record.extra_metadata,
        },
        "scope": SCOPE_SYSTEM,
        "owner_id": None,
        "source": source_tag,
        "doc_type": doc_type,
        "tags": record.theory_tags,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def load_existing_titles(vector_store, scope: str = SCOPE_SYSTEM) -> set:
    """加载 Qdrant 中已存在的 system scope titles（用于幂等检查）

    用于按 title 去重：如果新数据 title 已存在，跳过不重复写入。
    """
    records = vector_store.get_all_records()
    titles: set = set()
    for r in records:
        payload = r.payload or {}
        if payload.get("scope") == scope:
            t = payload.get("title")
            if t:
                titles.add(t)
    return titles


def seed_one_record(
    parser,
    embedding,
    vector_store,
    record: SeedRecord,
    source_tag: str,
    doc_type: str,
    existing_titles: set,
) -> SeedResult:
    """处理单条 seed 记录：解析 -> 分块 -> 向量化 -> 入库"""
    title = resolve_title(record)
    result = SeedResult(
        doc_id=record.doc_id,
        title=title,
        file_path=record.file_path,
        success=False,
    )

    # 幂等检查
    if title in existing_titles:
        result.skipped = True
        result.success = True
        return result

    # 解析文件
    try:
        text, _file_meta = parse_file_to_text(parser, record.file_path)
    except Exception as e:
        result.error = f"解析失败: {e}"
        return result

    if not text or not text.strip():
        result.error = "解析得到空文本"
        return result

    # 分块
    chunks = chunk_by_paragraph(text, record.doc_id)
    if not chunks:
        result.error = "分块后无有效内容"
        return result

    # 批量向量化
    try:
        texts = [c["content"] for c in chunks]
        embed_results = embedding.embed_batch(texts)
        vectors = [r.embedding for r in embed_results]
    except Exception as e:
        result.error = f"向量化失败: {e}"
        return result

    # 构造 VectorRecord 列表
    from app.services.rag.vector_store import VectorRecord

    records_to_upsert = []
    for chunk, vec in zip(chunks, vectors):
        payload = build_payload(record, chunk, source_tag, doc_type)
        qdrant_id = str(uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{source_tag}:{record.doc_id}:{chunk['chunk_id']}",
        ))
        records_to_upsert.append(VectorRecord(id=qdrant_id, vector=vec, payload=payload))

    # 入库
    try:
        ok = vector_store.upsert(records_to_upsert)
        if not ok:
            result.error = "upsert 返回 False"
            return result
    except Exception as e:
        result.error = f"入库失败: {e}"
        return result

    result.success = True
    result.chunks_written = len(records_to_upsert)
    existing_titles.add(title)  # 避免同批次内重复处理
    return result


def seed_batch(
    parser,
    embedding,
    vector_store,
    records: List[SeedRecord],
    source_tag: str,
    doc_type: str,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> Tuple[List[SeedResult], List[Dict]]:
    """批量处理 seed 记录

    dry_run=True 时只预览分块数，不真正入库
    limit 限制处理条数（用于测试）
    """
    if limit:
        records = records[:limit]

    # dry-run 也加载已存在 titles 以正确预览 skipped 状态
    existing_titles = load_existing_titles(vector_store)

    results: List[SeedResult] = []
    failures: List[Dict] = []

    total = len(records)
    for i, record in enumerate(records, 1):
        title = resolve_title(record)
        title_preview = title[:40] if title else record.doc_id

        if dry_run:
            result = SeedResult(
                doc_id=record.doc_id,
                title=title,
                file_path=record.file_path,
                success=True,
                skipped=title in existing_titles,
                chunks_written=0,
            )
            try:
                text, _ = parse_file_to_text(parser, record.file_path)
                chunks = chunk_by_paragraph(text, record.doc_id)
                result.chunks_written = len(chunks)
            except Exception as e:
                result.success = False
                result.error = f"解析预览失败: {e}"
                failures.append({
                    "doc_id": record.doc_id,
                    "title": title,
                    "file_path": record.file_path,
                    "reason": str(e),
                })

            status = "SKIP" if result.skipped else f"{result.chunks_written} chunks"
            if result.error:
                status = f"ERR: {result.error}"
            print(f"[{i}/{total}] dry-run {record.doc_id} {title_preview} -> {status}")
            results.append(result)
            continue

        # 真正入库
        result = seed_one_record(
            parser, embedding, vector_store,
            record, source_tag, doc_type, existing_titles,
        )
        results.append(result)

        if result.skipped:
            status = "SKIP (已存在)"
        elif result.success:
            status = f"{result.chunks_written} chunks"
        else:
            status = f"ERR: {result.error}"
            failures.append({
                "doc_id": record.doc_id,
                "title": title,
                "file_path": record.file_path,
                "reason": result.error or "unknown",
            })
        print(f"[{i}/{total}] {record.doc_id} {title_preview} -> {status}")

        # GC 控制
        if i % GC_EVERY_N_DOCS == 0:
            gc.collect()
            time.sleep(GC_SLEEP_SECONDS)

    return results, failures


def write_summary(
    results: List[SeedResult],
    failures: List[Dict],
    batch_name: str,
    output_dir: Path,
) -> Path:
    """写入结果摘要 JSON 文件"""
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"seed_{batch_name}_{ts}.json"

    summary = {
        "batch": batch_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "success": sum(1 for r in results if r.success and not r.skipped),
        "skipped": sum(1 for r in results if r.skipped),
        "failed": len(failures),
        "total_chunks_written": sum(r.chunks_written for r in results if not r.skipped),
        "results": [
            {
                "doc_id": r.doc_id,
                "title": r.title,
                "file_path": r.file_path,
                "success": r.success,
                "skipped": r.skipped,
                "chunks_written": r.chunks_written,
                "error": r.error,
            }
            for r in results
        ],
        "failures": failures,
    }
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path
