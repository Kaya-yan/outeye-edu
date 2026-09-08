"""任务A 交互有效性程序自检：结构契约校验 + 全课件交互多样性

防「看着像交互、点了没反应」：
1) 页内交互组件的标记结构必须与骨架 JS/CSS 的钩子契约匹配——词卡缺 .back、计时器缺
   .timer-display、解剖句缺 .cl 钩子等，该页带问题走重生成通道（≤2 轮）；
2) 全课件不同交互类型 ≥3 种：不足时挑最适合的页重生成一次（带缺失类型与用法提示），
   仍不足只记录不阻塞产出。

INTERACTION_CHECK_ENABLED 门控（默认开）；纯本地正则结构检查，零外部依赖。
新交互组件（如任务B 的 mark-words 等）在 INTERACTION_TYPE_MARKERS 与
page_interaction_problems 中登记即可计入两项校验。
"""

import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from loguru import logger

MIN_DISTINCT_TYPES = 3
MAX_STRUCTURAL_ROUNDS = 2

# 交互类型标记（页面 HTML 出现即计入该类型；同时用于多样性统计）
INTERACTION_TYPE_MARKERS: Dict[str, re.Pattern[str]] = {
    "reveal": re.compile(r"<details[^>]*class\s*=\s*[\"'][^\"']*\breveal\b", re.IGNORECASE),
    "timeline": re.compile(r"class\s*=\s*[\"'][^\"']*\btimeline\b", re.IGNORECASE),
    "vocab-card": re.compile(r"class\s*=\s*[\"'][^\"']*\bvocab-card\b", re.IGNORECASE),
    "timer": re.compile(r"class\s*=\s*[\"'][^\"']*\btimer\b|data-seconds\s*=", re.IGNORECASE),
    "anatomy": re.compile(r"class\s*=\s*[\"'][^\"']*\banatomy-sentence\b", re.IGNORECASE),
    "sent-walk": re.compile(r"class\s*=\s*[\"'][^\"']*\bsent-walk\b", re.IGNORECASE),
}

# 多样性补齐提示（重生成时告知 LLM 缺失类型的骨架用法）
TYPE_USAGE_HINTS: Dict[str, str] = {
    "reveal": "details.reveal 答案折叠（summary 提问 + 折叠内答案）",
    "timeline": "ol.timeline>li 时间线逐条点亮",
    "vocab-card": ".vocab-grid+.vocab-card 词卡翻转（front 词+音标 / back 释义例句）",
    "timer": ".timer[data-seconds] 计时器（内含 .timer-display 与 button）",
    "anatomy": ".anatomy-sentence 长难句点亮/X 光（cl cl-core/cl-mod 钩子）",
    "sent-walk": ".sent-walk 内 details/summary 逐句折叠细读",
}


def _cls_count(html: str, cls: str) -> int:
    return len(re.findall(rf'class\s*=\s*["\'][^"\']*\b{cls}\b[^"\']*["\']', html, re.IGNORECASE))


def _tag_count(html: str, tag: str) -> int:
    return len(re.findall(rf"<{tag}\b", html, re.IGNORECASE))


def page_interaction_problems(html: str) -> List[str]:
    """单页结构契约：每个已出现的交互组件，其骨架钩子必须齐备，否则点击无反应/展示退化"""
    problems: List[str] = []
    n_reveal = _cls_count(html, "reveal")
    if n_reveal and _tag_count(html, "summary") < n_reveal:
        problems.append(f"有 {n_reveal} 个 details.reveal 但 <summary> 不足（每个折叠必须配一个 summary，否则无法点击展开）")
    n_cards = _cls_count(html, "vocab-card")
    if n_cards:
        fronts, backs = _cls_count(html, "front"), _cls_count(html, "back")
        if fronts < n_cards or backs < n_cards:
            problems.append(f"{n_cards} 张 .vocab-card 需各配一对 .front/.back（正面词+音标、背面释义例句），当前 front {fronts} / back {backs}")
    # 计数排除 timer-display 等连字符后缀（\b 在连字符处也是词边界，会把 timer-display 误计为 timer）
    n_timers = len(re.findall(r'class\s*=\s*["\'][^"\']*\btimer\b(?!-)[^"\']*["\']', html, re.IGNORECASE))
    if n_timers:
        if _cls_count(html, "timer-display") < n_timers or _tag_count(html, "button") < n_timers:
            problems.append("每个 .timer 必须内含 .timer-display 与一个 <button>（启停按钮），否则计时器不可用")
        m_bad = re.search(r'data-seconds\s*=\s*["\']([^"\']*)["\']', html)
        if m_bad is None:
            problems.append(".timer 必须带 data-seconds 属性（秒数数字），否则计时器无时长")
        elif not re.fullmatch(r"\d{1,4}", m_bad.group(1)):
            problems.append(f'timer 的 data-seconds 必须是秒数数字（当前 "{m_bad.group(1)}"）')
    n_sent = _cls_count(html, "anatomy-sentence")
    if n_sent:
        n_core = _cls_count(html, "cl-core")
        n_cl = n_core + _cls_count(html, "cl-mod")
        if n_core < n_sent or n_cl < n_sent * 2:
            problems.append(f"{n_sent} 个 .anatomy-sentence 需各含 ≥1 个 cl-core 与合计 ≥2 个 .cl 跨度（点击点亮与 X 光透视依赖这些钩子）")
    if _cls_count(html, "timeline") and _tag_count(html, "li") < 2:
        problems.append("ol.timeline 至少要有 2 个 li（时间线逐条点亮）")
    if _cls_count(html, "sent-walk") and _tag_count(html, "details") > _tag_count(html, "summary"):
        problems.append("sent-walk 内每个 details 必须配 summary（点击展开依赖 summary）")
    return problems


def page_interaction_types(html: str) -> Set[str]:
    return {name for name, rx in INTERACTION_TYPE_MARKERS.items() if rx.search(html)}


def _pick_diversity_target(blueprint: List[Dict[str, Any]], total: int) -> int:
    """多样性不足时挑重生成页：优先互动页，其次语言聚焦/词汇页，最后任一内容页（跳过封面/总结）"""
    for prefer in (("interaction",), ("language_focus", "vocab"), ("lang_points", "text_anatomy")):
        for i, spec in enumerate(blueprint):
            if i < total and spec.get("kind") in prefer:
                return i
    for i, spec in enumerate(blueprint):
        if i < total and spec.get("kind") not in ("cover", "summary"):
            return i
    return 0


def run_interaction_check(
    pages: List[Any],
    *,
    blueprint: List[Dict[str, Any]],
    regen_page: Callable[[int, Any, List[str]], Optional[Any]],
    progress_cb: Optional[Callable[[str], None]] = None,
) -> Tuple[List[Any], Dict[str, Any]]:
    """交互有效性自检入口：返回（可能被重生成的页面列表, 摘要）；任何异常由调用方降级"""

    def _progress(msg: str) -> None:
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    pages = list(pages)
    total = len(pages)
    summary: Dict[str, Any] = {
        "enabled": True,
        "min_types": MIN_DISTINCT_TYPES,
        "types_found": [],
        "structural_problem_pages": {},
        "regenerated": {},
        "diversity_ok": True,
    }

    def _html(pg: Any) -> str:
        return getattr(pg, "html", "") or ""

    # ---- 相 1：结构契约（每页 ≤2 轮重生成，仍不合格保留并记录）----
    for i in range(total):
        rounds = 0
        while rounds < MAX_STRUCTURAL_ROUNDS:
            problems = page_interaction_problems(_html(pages[i]))
            if not problems:
                break
            summary["structural_problem_pages"][str(i + 1)] = problems
            rounds += 1
            _progress(f"交互自检：第 {i + 1} 页交互组件结构不完整，正在重生成（第 {rounds} 轮）…")
            try:
                rewritten = regen_page(i, pages[i], problems)
            except Exception as e:
                logger.warning(f"交互自检第 {i + 1} 页重生成异常（保留原稿）: {e}")
                break
            if rewritten is None:
                break
            pages[i] = rewritten
        if rounds:
            summary["regenerated"][str(i + 1)] = rounds

    # ---- 相 2：全课件交互多样性 ≥ MIN_DISTINCT_TYPES ----
    found: Set[str] = set()
    for pg in pages:
        found |= page_interaction_types(_html(pg))
    summary["types_found"] = sorted(found)
    summary["diversity_ok"] = len(found) >= MIN_DISTINCT_TYPES
    if not summary["diversity_ok"]:
        target = _pick_diversity_target(blueprint, total)
        missing = [t for t in INTERACTION_TYPE_MARKERS if t not in found]
        hints = "；".join(TYPE_USAGE_HINTS[t] for t in missing[:3] if t in TYPE_USAGE_HINTS)
        problem = (
            f"全课件交互类型仅 {len(found)} 种（要求 ≥{MIN_DISTINCT_TYPES}），学生全程被动看。"
            f"请在本页自然融入以下骨架交互组件之一（结构按类契约）：{hints}。"
            "不要为凑数硬塞，选与本页教学意图最匹配的一种。"
        )
        _progress(f"交互自检：全课件交互类型不足 {MIN_DISTINCT_TYPES} 种，正在补强第 {target + 1} 页…")
        try:
            rewritten = regen_page(target, pages[target], [problem])
        except Exception as e:
            logger.warning(f"交互自检多样性补强第 {target + 1} 页异常（保留原稿）: {e}")
            rewritten = None
        if rewritten is not None:
            pages[target] = rewritten
            summary["regenerated"][str(target + 1)] = summary["regenerated"].get(str(target + 1), 0) + 1
            found = set()
            for pg in pages:
                found |= page_interaction_types(_html(pg))
            summary["types_found"] = sorted(found)
            summary["diversity_ok"] = len(found) >= MIN_DISTINCT_TYPES
    logger.info(
        f"交互自检结果：交互类型 {summary['types_found']}，"
        f"结构问题页 {list(summary['structural_problem_pages']) or '无'}，"
        f"重生成 {summary['regenerated'] or '无'}，多样性{'达标' if summary['diversity_ok'] else '仍不足（已记录）'}"
    )
    return pages, summary
