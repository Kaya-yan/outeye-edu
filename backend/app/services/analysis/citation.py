"""
可追溯证据引用

将生成的教案各节与检索到的证据绑定：有证据则引用，无证据则显式降级（degraded）。
"""

import re
from typing import Dict, Any, List


def normalize_evidence(wiki_results: List[Dict], rag_results: List[Dict]) -> List[Dict[str, Any]]:
    """将 Wiki + RAG 结果归一化为统一的证据列表"""
    evidence = []
    for r in wiki_results or []:
        evidence.append({
            "source_type": "wiki",
            "title": r.get("title", ""),
            "content": (r.get("summary") or "")[:300],
            "score": r.get("relevance_score", 0),
        })
    for r in rag_results or []:
        meta = r.get("metadata", {}) or {}
        evidence.append({
            "source_type": "rag",
            "title": meta.get("title", ""),
            "content": (r.get("content") or "")[:300],
            "score": r.get("score", 0),
        })
    return evidence


def _relevance_score(section_text: str, evidence: Dict[str, Any]) -> float:
    """基于关键词重叠的简化相关性评分"""
    if not section_text or not evidence.get("title") or not evidence.get("content"):
        return 0.0

    # 提取中文双字词（bigram）+ 英文单词
    def tokens(text: str) -> set:
        text = text.lower()
        # 中文连续串拆为 bigram
        zh_runs = re.findall(r"[一-鿿]+", text)
        zh_bigrams = set()
        for run in zh_runs:
            for i in range(len(run) - 1):
                zh_bigrams.add(run[i:i + 2])
        en = re.findall(r"[a-z]{3,}", text)
        return zh_bigrams | set(en)

    section_tokens = tokens(section_text)
    evidence_text = f"{evidence['title']} {evidence['content']}"
    evidence_tokens = tokens(evidence_text)

    if not section_tokens or not evidence_tokens:
        return 0.0

    overlap = section_tokens & evidence_tokens
    return len(overlap) / max(len(section_tokens), 1)


def bind_evidence_to_section(section_text: str, evidence: List[Dict[str, Any]], threshold: float = 0.05) -> Dict[str, Any]:
    """为单个节绑定证据：有匹配则引用，无匹配则显式降级"""
    matched = []
    for e in evidence:
        score = _relevance_score(section_text, e)
        if score >= threshold:
            matched.append({
                "source_type": e["source_type"],
                "title": e["title"],
                "relevance": round(score, 3),
                "content": e["content"][:120],
            })

    if matched:
        # 按相关性降序
        matched.sort(key=lambda x: x["relevance"], reverse=True)
        return {"degraded": False, "citations": matched}
    return {"degraded": True, "citations": []}


def annotate_plan(plan: Dict[str, Any], wiki_results: List[Dict], rag_results: List[Dict]) -> Dict[str, Any]:
    """为教案各节添加证据标注（引用或降级）"""
    evidence = normalize_evidence(wiki_results, rag_results)

    # 教学建议（字符串列表 → 带证据的字典列表）
    suggestions = plan.get("teaching_suggestions", [])
    annotated_suggestions = []
    for s in suggestions:
        text = s if isinstance(s, str) else s.get("content", "")
        binding = bind_evidence_to_section(text, evidence)
        annotated_suggestions.append({
            "content": text,
            "evidence": binding["citations"],
            "degraded": binding["degraded"],
        })
    plan["teaching_suggestions"] = annotated_suggestions

    # 活动设计
    activities = plan.get("activity_designs", [])
    for activity in activities:
        if not isinstance(activity, dict):
            continue
        text = " ".join(str(v) for v in activity.values())
        binding = bind_evidence_to_section(text, evidence)
        activity["evidence"] = binding["citations"]
        activity["degraded"] = binding["degraded"]

    return plan
