"""
组件库驱动课件映射

将教案各节映射到官方教学组件（ComponentDefinition），替代硬编码 HTML 块。
"""

import re
from typing import Dict, Any, List, Optional


def _keyword_overlap(text: str, component: Dict[str, Any]) -> float:
    """基于中文 bigram 的简化相关性评分"""
    def tokens(s: str) -> set:
        s = s.lower()
        zh_runs = re.findall(r"[一-鿿]+", s)
        zh_bigrams = set()
        for run in zh_runs:
            for i in range(len(run) - 1):
                zh_bigrams.add(run[i:i + 2])
        return zh_bigrams | set(re.findall(r"[a-z]{3,}", s))

    text_tokens = tokens(text)
    comp_text = f"{component.get('name', '')} {component.get('summary', '')} {' '.join(component.get('subject_tags') or [])}"
    comp_tokens = tokens(comp_text)

    if not text_tokens or not comp_tokens:
        return 0.0
    return len(text_tokens & comp_tokens) / max(len(text_tokens), 1)


def resolve_component_for_section(
    teaching_stage: str,
    section_text: str,
    components: List[Dict[str, Any]],
    threshold: float = 0.05,
) -> Optional[Dict[str, Any]]:
    """为教案某节找到最匹配的教学组件（按教学阶段 + 关键词）"""
    candidates = [c for c in components if c.get("teaching_stage") == teaching_stage]
    if not candidates:
        return None

    best = None
    best_score = 0.0
    for c in candidates:
        score = _keyword_overlap(section_text, c)
        if score > best_score:
            best = c
            best_score = score

    if best is not None and best_score >= threshold:
        return best
    return None
