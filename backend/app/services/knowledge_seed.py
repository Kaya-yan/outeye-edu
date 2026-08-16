"""
系统知识种子

赛前播种匿名化的教学理论知识（system 作用域，全员可见，永久保留）。
"""

from datetime import datetime, timezone
from typing import List, Dict, Any

from loguru import logger

from app.core.scope import SCOPE_SYSTEM

# 匿名化系统种子：仅包含通用教学理论摘要，不含任何个人信息。
SYSTEM_SEED_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "title": "Krashen 输入假说",
        "scope": SCOPE_SYSTEM,
        "doc_type": "theory",
        "tags": ["输入假说", "i+1", "二语习得"],
        "content": (
            "输入假说主张语言习得发生在学习者接触到略高于其当前水平的可理解输入时，"
            "即 i+1。教学设计应提供丰富的、语境化的目标语输入，让学习者借助上下文自然理解新结构。"
            "输入应具备可理解性、趣味性与相关性，且不按语法顺序编排。"
        ),
    },
    {
        "title": "Bloom 认知目标分类",
        "scope": SCOPE_SYSTEM,
        "doc_type": "theory",
        "tags": ["认知目标", "Bloom 分类", "高阶思维"],
        "content": (
            "Bloom 分类学将认知过程分为记忆、理解、应用、分析、评价与创造六个层级。"
            "教学设计应从低阶认知目标逐步过渡到高阶认知目标，课堂提问与活动应覆盖不同层级，"
            "避免停留在记忆与理解层面。"
        ),
    },
    {
        "title": "认知负荷理论",
        "scope": SCOPE_SYSTEM,
        "doc_type": "theory",
        "tags": ["认知负荷", "工作记忆", "支架"],
        "content": (
            "认知负荷理论区分内在负荷、外在负荷与相关负荷。教学应降低外在负荷（如清晰的呈现、"
            "去除冗余信息），管理工作记忆容量，并把认知资源导向与学习目标相关的加工。"
            "对初学者应提供更多支架，随着熟练度提升逐步撤除。"
        ),
    },
    {
        "title": "CEFR 语言能力框架",
        "scope": SCOPE_SYSTEM,
        "doc_type": "theory",
        "tags": ["CEFR", "语言能力等级", "评估标准"],
        "content": (
            "CEFR 将语言能力分为 A1 至 C2 六个等级，从基础使用者到熟练使用者。"
            "教学设计应根据学习者等级设定恰当的语言输入难度、任务复杂度与评估标准，"
            "确保目标可达成且具有适度挑战。"
        ),
    },
    {
        "title": "支架式教学",
        "scope": SCOPE_SYSTEM,
        "doc_type": "theory",
        "tags": ["支架式教学", "ZPD", "最近发展区"],
        "content": (
            "支架式教学基于最近发展区（ZPD）理论，教师在学习者无法独立完成的任务上提供临时支持，"
            "随能力提升逐步撤除支架。常见支架包括示范、提示、框架性提问与合作学习。"
        ),
    },
]


def seed_system_knowledge(vector_store, embedding_service) -> Dict[str, Any]:
    """将系统种子文档写入向量库（scope=system），幂等：已存在则跳过。"""
    from app.services.rag.document_parser import DocumentParser
    from app.services.rag.vector_store import VectorRecord

    # 幂等检查：已有 system 作用域记录则跳过
    try:
        existing = vector_store.get_all_records()
        if any((r.payload or {}).get("scope") == SCOPE_SYSTEM for r in existing):
            logger.info("系统知识种子已存在，跳过播种")
            return {"seeded": 0, "skipped": True}
    except Exception as e:
        logger.warning(f"检查系统种子失败，继续播种: {e}")

    parser = DocumentParser()
    seeded = 0
    now = datetime.now(timezone.utc).isoformat()

    for doc in SYSTEM_SEED_DOCUMENTS:
        try:
            parsed = parser.parse_text(text=doc["content"], title=doc["title"])
            records = []
            for chunk in parsed.chunks:
                embed_result = embedding_service.embed_text(chunk.content)
                payload = {
                    "doc_id": chunk.doc_id,
                    "content": chunk.content,
                    "title": doc["title"],
                    "metadata": chunk.metadata,
                    "scope": SCOPE_SYSTEM,
                    "owner_id": None,
                    "source": "system_seed",
                    "doc_type": doc.get("doc_type", "theory"),
                    "tags": doc.get("tags", []),
                    "created_at": now,
                }
                records.append(VectorRecord(
                    id=chunk.id,
                    vector=embed_result.embedding,
                    payload=payload,
                ))
            if records:
                vector_store.upsert(records)
                seeded += 1
        except Exception as e:
            logger.error(f"播种系统文档失败: {doc['title']}: {e}")

    logger.info(f"系统知识播种完成: {seeded} 篇")
    return {"seeded": seeded, "skipped": False}
