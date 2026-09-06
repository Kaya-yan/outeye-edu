"""S7 全局一致性审校：术语统一（文本节点词边界替换 + 结构校验回滚）+ 结构类意见存档

LLM 读整套课件文本，产出术语规范表与结构意见。术语替换只发生在
HTML 文本节点（标签、属性、class 不动），拉丁词加词边界；替换后做
结构校验（页数不变、无新增危险片段、体积 sane），失败整笔回滚。
结构意见不自动改动，随 meta.consistency_review 提示教师。
开关 CONSISTENCY_REVIEW_ENABLED 关闭即整层跳过；任何异常原样返回。
"""

import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger

from app.services.prompt_manager import prompt_version, render_prompt

CONSISTENCY_PROMPT_NAME = "courseware_consistency_v1"
MAX_TERMS = 8
MAX_NOTES = 6


def _term_pattern(variant: str) -> "re.Pattern[str]":
    esc = re.escape(variant)
    if variant and re.match(r"[A-Za-z]", variant[0]):
        esc = r"\b" + esc
    if variant and re.match(r"[A-Za-z]", variant[-1]):
        esc = esc + r"\b"
    return re.compile(esc)


def _replace_in_text_nodes(html: str, variants: Dict[str, str]) -> Tuple[str, Dict[str, int], int]:
    """只在文本节点替换（标签与属性不动）：按标签切分，偶数段是文本"""
    parts = re.split(r"(<[^>]*>)", html)
    per_variant: Dict[str, int] = {v: 0 for v in variants}
    for i in range(0, len(parts), 2):
        seg = parts[i]
        if not seg:
            continue
        for variant, canonical in variants.items():
            seg, n = _term_pattern(variant).subn(canonical, seg)
            per_variant[variant] += n
        parts[i] = seg
    return "".join(parts), per_variant, sum(per_variant.values())


def _structure_ok(orig: str, new: str) -> bool:
    if orig.count('<section class="page"') != new.count('<section class="page"'):
        return False
    if len(new) > len(orig) * 1.2 + 100:
        return False
    for forbidden in ("<script", "javascript:", "onerror=", "onload="):
        if forbidden in new and forbidden not in orig:
            return False
    return True


def _pages_digest(html: str, per_page: int = 220, total_cap: int = 6000) -> str:
    chunks = []
    for i, m in enumerate(re.finditer(r'<section class="page"[^>]*>(.*?)(?=<section class="page"|\Z)', html, re.S), 1):
        text = re.sub(r"<[^>]+>", " ", m.group(1))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            chunks.append(f"【第 {i} 页】{text[:per_page]}")
        if sum(len(c) for c in chunks) > total_cap:
            break
    return "\n".join(chunks)[:total_cap]


def _parse_review(answer: str) -> Optional[Dict[str, Any]]:
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", answer, re.S)
    raw = m.group(1) if m else answer.strip()
    try:
        data = json.loads(raw)
    except Exception:
        return None
    terms = []
    for t in (data.get("terminology") or [])[:MAX_TERMS]:
        if not isinstance(t, dict):
            continue
        canonical = str(t.get("canonical", "")).strip()
        variants = [str(v).strip() for v in (t.get("variants") or []) if str(v).strip()]
        variants = [v for v in variants if v != canonical and len(v) >= 2]
        if canonical and variants:
            terms.append({"canonical": canonical, "variants": variants})
    notes = [str(n).strip() for n in (data.get("structure_notes") or []) if str(n).strip()][:MAX_NOTES]
    return {"terminology": terms, "structure_notes": notes}


def run_consistency_review(
    generator: Any,
    *,
    html: str,
    title: str,
    language_name: str = "英语",
    student_level: str = "",
    progress_cb: Optional[Callable[[str], None]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """入口：返回（可能已做术语统一的 html, 审校摘要）；异常一律原样返回"""

    def _progress(msg: str) -> None:
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    summary: Dict[str, Any] = {"enabled": True, "version": prompt_version(CONSISTENCY_PROMPT_NAME)}
    try:
        _, user_prompt = render_prompt(
            CONSISTENCY_PROMPT_NAME,
            title=title,
            language_name=language_name,
            student_level=student_level or "未知",
            pages_digest=_pages_digest(html),
        )
        system_prompt, _ = render_prompt(CONSISTENCY_PROMPT_NAME)
        answer, _ = generator._generate_with_api([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        review = _parse_review(answer)
        if review is None:
            summary["note"] = "审校输出不可解析，未做任何改动"
            return html, summary

        summary["structure_notes"] = review["structure_notes"]
        summary["terminology"] = review["terminology"]
        summary["replacements"] = {}
        if not review["terminology"]:
            return html, summary

        variants: Dict[str, str] = {}
        for t in review["terminology"]:
            for v in t["variants"]:
                variants.setdefault(v, t["canonical"])
        new_html, per_variant, total = _replace_in_text_nodes(html, variants)
        summary["replacements"] = {v: n for v, n in per_variant.items() if n}
        summary["total_replaced"] = total
        if total == 0:
            summary["note"] = "术语变体未在课件中命中，未改动"
            return html, summary
        if not _structure_ok(html, new_html):
            summary["rolled_back"] = True
            summary["note"] = "替换后结构校验未过，已整笔回滚"
            return html, summary
        _progress(f"全局审校完成：统一了 {total} 处术语表述")
        return new_html, summary
    except Exception as e:
        logger.warning(f"全局一致性审校异常，原样返回: {e}")
        summary["error"] = str(e)[:200]
        return html, summary
