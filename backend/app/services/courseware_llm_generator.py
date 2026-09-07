"""
课件 LLM 生成引擎（FIX-3 · F3.1/F3.2；HTML 链路 ④a 三层架构 + ③ 两阶段生成）

HTML 链路（③ 两阶段 · 三层）：框架层+主题层写死在 courseware_skeleton_v2.html
（16:9 舞台、翻页/键盘/页码、交互行为、逐段精讲组件），LLM 分两阶段工作——
阶段一规划器（courseware_page_planner_v1）一次调用产出页面蓝图（页型/标题/
意图/段落锚点/强调色），程序硬校验（段落全覆盖 + ≤25 页截断），失败带原因
重试一次，仍失败确定性回退蓝图；阶段二按蓝图逐页生成
（courseware_html_page_v2，含金标准 few-shot），3 路并发，每页带段落原文与
白盒切片（难词归属小写化+词干匹配、长难句按长度+从句标记数加权排序）。
逐页程序自检（单焦点/禁忌/行内色值），不合格定向重生成 ≤2 轮，仍失败确定
性净化，完全无输出用程序兜底页保证整副不缺页；任意阶段异常回退
courseware_bootstrap，fallback=True 由前端标注"简化版生成"，绝不静默。
PPT 链路（F3.3）：LLM 逐页大纲 JSON（≤6 要点/页、口语化讲者备注）
→ python-pptx 渲染 16:9；校验失败重试一次，仍失败回退确定性大纲。
Word 链路（F3.4）后续在此模块追加。
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from html import escape as _html_escape
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4
from loguru import logger
import json
import re
import time

from app.services.prompt_manager import render_prompt, prompt_version
from app.services.analysis.fusion_generator import _esc, prepare_text
from app.services.courseware_themes import DEFAULT_THEME_ID, CoursewareTheme, get_theme
from app.services.teacher_intent import intent_prompt_section

PLANNER_PROMPT_NAME = "courseware_page_planner_v1"
PAGE_PROMPT_NAME = "courseware_html_page_v2"
MAX_BLUEPRINT_PAGES = 25

_EXTERNAL_RE = re.compile(r"(?:src|href)\s*=\s*[\"']https?://|@import|<link[^>]+stylesheet", re.IGNORECASE)

# ============ ④a 三层架构：骨架（框架+主题）与内容层分离 ============

_SKELETON_PATH = Path(__file__).resolve().parent / "courseware_skeleton_v2.html"
_SKELETON_CACHE: Optional[str] = None

# 默认主题（academic）的基线 token；主题库见 courseware_themes.py
_ACADEMIC = get_theme(DEFAULT_THEME_ID)
THEME_PAPER = _ACADEMIC.tokens["paper"]
THEME_TOKENS = {k: _ACADEMIC.tokens[k] for k in ("paper", "ink", "text", "muted")}
ACCENT_PALETTE = {"#b5493e": "朱砂红", "#3e6b5a": "黛绿", "#99653a": "暖赭", "#35507a": "绀青"}
DEFAULT_ACCENT = _ACADEMIC.default_accent


@dataclass
class HTMLCoursewareResult:
    html: str
    editor_schema: Dict[str, Any]
    structure_sync: Dict[str, Any]
    self_check: Dict[str, Any] = field(default_factory=dict)
    prompt_version: str = ""
    model: str = ""
    fallback: bool = False
    retries: int = 0
    generation_duration: float = 0.0


def _format_plan_text(plan: Dict[str, Any]) -> str:
    """把结构化教案渲染为 LLM 可读的完整文本（课件内容的唯一来源）"""
    parts: List[str] = []

    if plan.get("framework"):
        parts += ["【教学设计框架】", str(plan["framework"])]
    objectives = plan.get("objectives") or []
    if objectives:
        parts.append("【教学目标】")
        for i, o in enumerate(objectives, 1):
            if isinstance(o, dict):
                line = f"目标{i}：{o.get('text', '')}"
                if o.get("bloom"):
                    line += f"（Bloom：{o['bloom']}）"
                if o.get("assessment"):
                    line += f"\n  评估方式：{o['assessment']}"
                parts.append(line)
            else:
                parts.append(f"目标{i}：{o}")
    if plan.get("difficulty_overview"):
        parts += ["【课文难度概述】", str(plan["difficulty_overview"])]

    suggestions = plan.get("teaching_suggestions") or []
    if suggestions:
        parts.append("【教学建议】")
        parts += [f"{i}. {s}" for i, s in enumerate(suggestions, 1)]

    parts.append("【课堂环节设计】")
    for i, act in enumerate(plan.get("activity_designs") or [], 1):
        if not isinstance(act, dict):
            parts.append(f"环节{i}：{act}")
            continue
        header = f"环节{i}：{act.get('name', '')}（{act.get('duration', '时长未标注')}）"
        parts.append(header)
        if act.get("objective"):
            parts.append(f"- 目标：{act['objective']}")
        if act.get("steps"):
            parts.append(f"- 步骤：{act['steps']}")
        if act.get("assessment"):
            parts.append(f"- 评估点：{act['assessment']}")

    assessment = plan.get("assessment") or {}
    formative = assessment.get("formative") or []
    summative = assessment.get("summative") or []
    if formative or summative:
        parts.append("【评估设计】")
        if formative:
            parts.append("形成性：" + "；".join(formative))
        if summative:
            parts.append("终结性：" + "；".join(summative))

    if plan.get("differentiation"):
        parts += ["【差异化教学策略】", str(plan["differentiation"])]
    if plan.get("theoretical_basis"):
        parts += ["【理论依据】", str(plan["theoretical_basis"])]

    return "\n".join(parts)


def _build_metrics_lines(analysis: Dict[str, Any]) -> str:
    """白盒关键指标精简行（供 LLM 取材，不重复教案已有内容）"""
    lines = []
    vocab = analysis.get("vocabulary") or {}
    difficult = ", ".join(
        d.get("word", "") for d in (vocab.get("difficult_words") or [])[:10]
    )
    if difficult:
        lines.append(f"- 难点词（前10）：{difficult}")
    if vocab.get("total_words"):
        lines.append(f"- 总词数 {vocab.get('total_words')}，不重复词 {vocab.get('unique_words')}")
    syntax = analysis.get("syntax") or {}
    max_sent = syntax.get("max_sentence") or {}
    if max_sent.get("preview"):
        lines.append(
            f"- 最长句（第{(max_sent.get('index') or 0) + 1}句，{max_sent.get('word_count')}词）：\"{str(max_sent.get('preview'))[:80]}\""
        )
    if syntax.get("avg_sentence_length"):
        lines.append(f"- 平均句长 {syntax['avg_sentence_length']} 词")
    discourse = analysis.get("discourse") or {}
    if discourse.get("genre_hint"):
        lines.append(f"- 体裁提示：{discourse['genre_hint']}，共 {discourse.get('paragraph_count', '?')} 段")
    return "\n".join(lines) or "-（无白盒指标）"


def _build_components_digest(components: List[Dict[str, Any]]) -> str:
    lines = []
    for c in components or []:
        level = c.get("interaction_level") or "static"
        lines.append(f"- {c.get('slug')} — {c.get('summary') or c.get('name')}（交互：{level}）")
    return "\n".join(lines) or "-（组件库为空，按约束规范自行设计原生交互）"


# ---- 内容层解析与程序自检（④a：框架项由骨架保证，只查内容页） ----

@dataclass
class _ContentPage:
    title: str
    intent: str
    html: str


_ACCENT_DECL_RE = re.compile(r"ACCENT\s*[:：]\s*(#[0-9a-fA-F]{6})")
_PAGE_META_RE = re.compile(r"<!--\s*page\s*[:：]\s*\d+\s*(?:\|\s*(.*?))?\s*-->", re.IGNORECASE)
_PAGE_INTENT_RE = re.compile(r"<!--\s*intent\s*[:：]\s*(.*?)\s*-->", re.IGNORECASE)
_RAW_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgb[a]?\s*\(|\bhsl[a]?\s*\(")
_GRADIENT_RE = re.compile(r"gradient\s*\(", re.IGNORECASE)
# ASCII 构造 emoji 区段，避免在源码嵌非 ASCII 字符区间（编辑易损坏）
_EMOJI_RE = re.compile(
    "["
    + chr(0x2600) + "-" + chr(0x27BF)
    + chr(0x2B00) + "-" + chr(0x2BFF)
    + chr(0xFE0F)
    + chr(0x1F000) + "-" + chr(0x1FAFF)
    + "]"
)
_FORBIDDEN_TAGS_RE = re.compile(r"<\s*(script|style|link|iframe|object|embed)\b", re.IGNORECASE)
_EVENT_ATTR_RE = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)
_INLINE_STYLE_FORBIDDEN_RE = re.compile(
    r"style\s*=\s*[\"'][^\"']*\b(color|background|font-family|line-height)", re.IGNORECASE
)
_PAGE_FOCUS_RE = re.compile(r"class\s*=\s*[\"'][^\"']*\bpage-focus\b")
_INTERACTION_MARKERS = {
    "reveal": re.compile(r"<details[^>]*class\s*=\s*[\"'][^\"']*\breveal\b", re.IGNORECASE),
    "timeline": re.compile(r"class\s*=\s*[\"'][^\"']*\btimeline\b", re.IGNORECASE),
    "vocab-card": re.compile(r"class\s*=\s*[\"'][^\"']*\bvocab-card\b", re.IGNORECASE),
    "timer": re.compile(r"class\s*=\s*[\"'][^\"']*\btimer\b|data-seconds\s*=", re.IGNORECASE),
    "anatomy": re.compile(r"class\s*=\s*[\"'][^\"']*\banatomy-sentence\b", re.IGNORECASE),
    "sent-walk": re.compile(r"class\s*=\s*[\"'][^\"']*\bsent-walk\b", re.IGNORECASE),
}


def _parse_pages(answer: str) -> Tuple[str, List[_ContentPage]]:
    """解析内容层输出：ACCENT 声明 + 逐页 ```html 块。

    页注释（page/intent）契约在块内前两行；模型偏离写在围栏外时回看
    上一围栏结束到本围栏开始之间的文本兜底。
    """
    pages: List[_ContentPage] = []
    prev_end = 0
    for m_fence in re.finditer(r"```html\s*(.*?)\s*```", answer, re.DOTALL | re.IGNORECASE):
        block = m_fence.group(1)
        m_meta = _PAGE_META_RE.search(block[:400])
        m_intent = _PAGE_INTENT_RE.search(block[:400])
        content = block
        if m_meta or m_intent:
            for m in (m_meta, m_intent):
                if m:
                    content = content.replace(m.group(0), "", 1)
        else:
            lookback = answer[prev_end:m_fence.start()][-400:]
            m_meta = _PAGE_META_RE.search(lookback)
            m_intent = _PAGE_INTENT_RE.search(lookback)
        pages.append(
            _ContentPage(
                title=(m_meta.group(1).strip() if m_meta and m_meta.group(1) else ""),
                intent=(m_intent.group(1).strip() if m_intent else ""),
                html=content.strip(),
            )
        )
        prev_end = m_fence.end()
    m_accent = _ACCENT_DECL_RE.search(answer)
    accent = (m_accent.group(1).lower() if m_accent else "")
    return accent, pages


def _interaction_types(pages: List[_ContentPage]) -> Set[str]:
    all_html = "\n".join(p.html for p in pages)
    return {name for name, rx in _INTERACTION_MARKERS.items() if rx.search(all_html)}


def _validate_content_page(page: _ContentPage) -> List[str]:
    """单页程序自检：单焦点 / 无脚本 / 无事件属性 / 无行内色值 / 无渐变 / 无 emoji / 无外链"""
    problems = []
    focus_count = len(_PAGE_FOCUS_RE.findall(page.html))
    if focus_count != 1:
        problems.append(f"必须恰好一个 .page-focus，实际 {focus_count} 个")
    if len(page.html) < 120:
        problems.append("内容过短（<120 字符），疑似截断")
    if _FORBIDDEN_TAGS_RE.search(page.html):
        problems.append("含禁用标签（script/style/link/iframe 等），行为与样式由骨架负责")
    if _EVENT_ATTR_RE.search(page.html):
        problems.append("含事件属性（on*=）")
    if _RAW_COLOR_RE.search(page.html):
        problems.append("含行内色值（#hex/rgb()/hsl()），颜色只能用 var(--token)")
    if _GRADIENT_RE.search(page.html):
        problems.append("含渐变")
    if _EMOJI_RE.search(page.html):
        problems.append("含 emoji 或装饰性符号")
    if _INLINE_STYLE_FORBIDDEN_RE.search(page.html):
        problems.append("行内 style 含禁用属性（color/background/font-family/line-height）")
    if _EXTERNAL_RE.search(page.html):
        problems.append("含外链资源，违反单文件约束")
    return problems


def _sanitize_page(html_str: str) -> str:
    """重生成仍失败时的兜底净化：确定性剥除脚本/事件/违禁行内样式/emoji，保证硬性红线"""
    s = re.sub(r"<script\b.*?</script>|<style\b.*?</style>|<iframe\b.*?</iframe>", "", html_str, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"<\s*(link|object|embed)\b[^>]*/?>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\son[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", s, flags=re.IGNORECASE)
    s = re.sub(r"style\s*=\s*(\"[^\"]*\b(?:color|background|font-family|line-height|gradient)[^\"]*\"|'[^']*\b(?:color|background|font-family|line-height|gradient)[^']*')", "", s, flags=re.IGNORECASE)
    s = _EMOJI_RE.sub("", s)
    return s.strip()


def _load_skeleton() -> str:
    global _SKELETON_CACHE
    if _SKELETON_CACHE is None:
        _SKELETON_CACHE = _SKELETON_PATH.read_text(encoding="utf-8")
    return _SKELETON_CACHE


def _blend_colors(hex_fg: str, hex_bg: str, ratio: float) -> str:
    fg = [int(hex_fg[i:i + 2], 16) for i in (1, 3, 5)]
    bg = [int(hex_bg[i:i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(ratio * fg[i] + (1 - ratio) * bg[i]) for i in range(3)]
    return "#" + "".join(f"{c:02x}" for c in mixed)


def _assemble_skeleton(title: str, accent: str, pages: List[_ContentPage], theme: Optional[CoursewareTheme] = None) -> str:
    """三层拼装：骨架（框架）+ 主题 token 组与微调（④b）+ 逐页内容 section（重编页码）"""
    theme = theme or _ACADEMIC
    sections = []
    for i, p in enumerate(pages, 1):
        attrs = f'<section class="page" data-page="{i}" data-title="{_html_escape(p.title or f"第{i}页", quote=True)}"'
        if p.intent:
            attrs += f' data-intent="{_html_escape(p.intent, quote=True)}"'
        sections.append(f'{attrs}>\n{p.html}\n</section>')
    token_block = (
        theme.token_css()
        + f"\n  --accent:{accent};\n  --accent-soft:{_blend_colors(accent, theme.tokens['paper'], 0.12)};"
    )
    html = _load_skeleton().replace("<!--SECTIONS-->", "\n".join(sections))
    return (
        html.replace("__TITLE__", _html_escape(title))
        .replace("__TOKEN_BLOCK__", token_block)
        .replace("__THEME_EXTRA__", theme.extra_css)
    )


def _relative_luminance(hex_color: str) -> float:
    def channel(c: int) -> float:
        v = c / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    """WCAG 对比度；主题 token 组合在测试中断言 ≥4.5:1（内容层禁行内色值即承袭该保证）"""
    la, lb = _relative_luminance(hex_a), _relative_luminance(hex_b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _regen_page(generator: Any, system_prompt: str, user_prompt: str, page: _ContentPage, index: int, problems: List[str]) -> Optional[_ContentPage]:
    """单页定向重生成：成功且通过自检才替换，否则返回 None（调用方保留原稿）"""
    user = (
        f"{user_prompt}\n\n"
        f"以下是课件第 {index} 页（标题：{page.title or '无'}，教学意图：{page.intent or '无'}）的现有内容：\n"
        f"```html\n{page.html}\n```\n\n"
        "程序自检发现以下问题：\n" + "\n".join(f"- {p}" for p in problems) + "\n\n"
        "请只重写这一页的内容区 HTML，修复上述全部问题，教学设计保持不变。"
        "输出：一个 ```html 代码块（块内前两行仍是页注释 page/intent），此外不输出任何文字。"
        "提醒：颜色只用 var(--ink/--text/--muted/--paper/--accent/--line)；禁止 script/style/link/iframe、"
        "事件属性、行内色值、渐变、emoji、外链；每页恰好一个 .page-focus。"
    )
    answer, _usage = generator._generate_with_api(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user}]
    )
    _, pages = _parse_pages(answer)
    if len(pages) != 1:
        return None
    if _validate_content_page(pages[0]):
        return None
    return pages[0]


# ============ ③ 两阶段：确定性切片（程序算，规划器与逐页提示词引用） ============

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[\"'A-Za-z一-鿿])")
_CLAUSE_MARKER_RE = re.compile(
    r"\b(?:which|that|who|whom|whose|where|when|while|although|though|whereas|because|since|unless|before|after|despite|whereby)\b|;",
    re.IGNORECASE,
)


def _simple_stem(word: str) -> str:
    """小写化 + 简单词干（难词段落归属用）：spreading/spreads → spread 类变形归并"""
    w = re.sub(r"[^a-z\-]", "", word.lower())
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    for suf in ("ing", "ed", "es", "er", "est"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)]
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us")):
        return w[:-1]
    return w


def _word_in_paragraph(word: str, tokens: List[str]) -> bool:
    """难词归属匹配：小写化 + 词干相等，或共享 ≥4 字符前缀（note/notes 类屈折）"""
    ws = _simple_stem(word)
    for t in tokens:
        if word.lower() == t.lower() or ws == _simple_stem(t):
            return True
        ts = _simple_stem(t)
        if min(len(ws), len(ts)) >= 4 and (ws.startswith(ts) or ts.startswith(ws)):
            return True
    return False


def _split_paragraphs(text: str) -> List[str]:
    """确定性分段：≥1 个空行切段、段内空白归一；过短片段并入前段（开头则与后段合并），不丢内容"""
    paras: List[str] = []
    pending = ""
    for raw in re.split(r"\n\s*\n", text or ""):
        p = re.sub(r"\s+", " ", raw).strip()
        if not p:
            continue
        if pending:
            p = (pending + " " + p).strip()
            pending = ""
        if len(p.split()) >= 5:
            paras.append(p)
        elif paras:
            paras[-1] = paras[-1] + " " + p
        else:
            pending = p
    if pending:
        paras.append(pending)
    return paras


def _split_sentences(paragraph: str) -> List[str]:
    return [s.strip() for s in _SENT_SPLIT_RE.split(paragraph) if len(s.strip().split()) >= 3]


def _long_sentence_score(sentence: str) -> int:
    """长难句加权：长度 + 3×从句标记数（微调 a）"""
    return len(sentence.split()) + 3 * len(_CLAUSE_MARKER_RE.findall(sentence))


def _slice_analysis(paragraphs: List[str], analysis: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """白盒指标按段落归属切片：难词归属（小写化+词干匹配）、长难句（加权排序取前 2）"""
    analysis = analysis or {}
    difficult = [
        str(d.get("word", "")).strip()
        for d in ((analysis.get("vocabulary") or {}).get("difficult_words") or [])
        if isinstance(d, dict) and d.get("word")
    ]
    slices: List[Dict[str, Any]] = []
    for i, para in enumerate(paragraphs, 1):
        tokens = [t for t in re.split(r"[^A-Za-z\-']+", para) if t]
        words = [w for w in difficult if _word_in_paragraph(w, tokens)]
        ranked = sorted(_split_sentences(para), key=_long_sentence_score, reverse=True)
        long_sents = [s for s in ranked if _long_sentence_score(s) >= 24][:2]
        slices.append({
            "index": i,
            "preview": (para[:120] + "…") if len(para) > 120 else para,
            "word_count": len(para.split()),
            "difficult_words": words,
            "long_sentences": long_sents,
        })
    return slices


# ============ ③ 两阶段：页面蓝图（规划器 LLM + 程序硬校验 + 确定性回退） ============

PAGE_KINDS = ("cover", "agenda", "vocab", "deep_reading", "language_focus", "interaction", "summary")
KIND_LABELS = {
    "cover": "封面页",
    "agenda": "目标页",
    "vocab": "词汇预教页",
    "deep_reading": "精讲页",
    "language_focus": "语言聚焦页",
    "interaction": "互动检测页",
    "summary": "总结页",
}


def _page_progress_label(spec: Dict[str, Any]) -> str:
    """进度文案显示当前页类型（微调 c），如「第 3 段精讲页」「目标页」"""
    if spec.get("kind") == "deep_reading" and spec.get("para"):
        idxs = spec["para"]
        if len(idxs) > 1:
            return f"第{idxs[0]}-{idxs[-1]}段精讲页"
        return f"第{idxs[0]}段精讲页"
    return KIND_LABELS.get(spec.get("kind", ""), "内容页")


def _normalize_blueprint(data: Dict[str, Any], n_paras: int) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """规划器输出 → 合法蓝图，返回 (蓝图, 失败原因)。程序只管硬契约：页型合法、
    段落全覆盖、首封面末总结、≤25 页截断；页数多少由 LLM 在区间内自主决定"""
    if not isinstance(data, dict):
        return None, "输出不是 JSON 对象"
    pages_raw = data.get("pages")
    if not isinstance(pages_raw, list) or not pages_raw:
        return None, "pages 缺失或为空"
    pages: List[Dict[str, Any]] = []
    for p in pages_raw:
        if not isinstance(p, dict):
            continue
        kind = str(p.get("kind", "")).strip()
        if kind not in PAGE_KINDS:
            continue
        para: Optional[List[int]] = None
        if kind in ("deep_reading", "language_focus"):
            raw_para = p.get("para")
            if isinstance(raw_para, int) and 1 <= raw_para <= n_paras:
                para = [raw_para]
            elif isinstance(raw_para, list):
                para = sorted({x for x in raw_para if isinstance(x, int) and 1 <= x <= n_paras})
            if kind == "deep_reading" and not para:
                continue  # 精讲页必须有合法段落锚点
        pages.append({
            "kind": kind,
            "title": str(p.get("title", "")).strip()[:40],
            "intent": str(p.get("intent", "")).strip()[:120],
            "para": para,
        })
    if not pages:
        return None, "无合法页面"
    covered = {x for spec in pages if spec["kind"] == "deep_reading" for x in (spec["para"] or [])}
    missing = [i for i in range(1, n_paras + 1) if i not in covered]
    if missing:
        return None, f"段落未被精讲页覆盖：第 {missing[:8]} 段"
    if pages[0]["kind"] != "cover":
        pages.insert(0, {"kind": "cover", "title": "", "intent": "建立主题情境", "para": None})
    if pages[-1]["kind"] != "summary":
        pages.append({"kind": "summary", "title": "总结与作业", "intent": "回收目标并布置作业", "para": None})
    if len(pages) > MAX_BLUEPRINT_PAGES:
        # 溢出裁剪优先级：互动 < 语言聚焦/词汇/目标 < 精讲 < 封面/总结
        keep_priority = {"interaction": 0, "language_focus": 1, "vocab": 1, "agenda": 1, "deep_reading": 2, "cover": 3, "summary": 3}
        overflow = len(pages) - MAX_BLUEPRINT_PAGES
        drop = set(sorted(
            range(len(pages)),
            key=lambda i: (keep_priority.get(pages[i]["kind"], 0), -i),
        )[:overflow])
        pages = [spec for i, spec in enumerate(pages) if i not in drop]
    return pages, ""


def _fallback_blueprint(slices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """确定性回退蓝图：封面/目标/词汇预教/逐段精讲/检测/总结；段落多时并段保 25 页上限"""
    pages: List[Dict[str, Any]] = [
        {"kind": "cover", "title": "", "intent": "建立主题情境，激活已知", "para": None},
        {"kind": "agenda", "title": "学习目标", "intent": "明确本课结束时学生能做到什么", "para": None},
    ]
    if any(s["difficult_words"] for s in slices):
        pages.append({"kind": "vocab", "title": "词汇预教", "intent": "预教难点词，先建立词形识别", "para": None})
    budget = max(MAX_BLUEPRINT_PAGES - len(pages) - 2, 1)  # 给检测页与总结页留位
    per_page = max(1, -(-len(slices) // budget))
    for start in range(0, len(slices), per_page):
        idxs = [s["index"] for s in slices[start:start + per_page]]
        pages.append({
            "kind": "deep_reading",
            "title": f"第{idxs[0]}段精讲" if len(idxs) == 1 else f"第{idxs[0]}-{idxs[-1]}段精讲",
            "intent": "逐段细读：原文、主旨、长难句、语言点、衔接",
            "para": idxs,
        })
    pages.append({"kind": "interaction", "title": "理解检测", "intent": "基于课文命题，检验理解", "para": None})
    pages.append({"kind": "summary", "title": "总结与作业", "intent": "回收目标并布置作业", "para": None})
    return pages


def _paragraphs_digest(slices: List[Dict[str, Any]]) -> str:
    lines = []
    for s in slices:
        line = f"- 第{s['index']}段（{s['word_count']}词）：{s['preview']}"
        if s["difficult_words"]:
            line += f"｜难点词：{'、'.join(s['difficult_words'][:6])}"
        if s["long_sentences"]:
            line += f"｜长难句：{s['long_sentences'][0][:70]}…"
        lines.append(line)
    return "\n".join(lines) or "-（无段落）"


def _objectives_digest(plan: Dict[str, Any]) -> str:
    lines = []
    for i, o in enumerate(plan.get("objectives") or [], 1):
        text = o.get("text", "") if isinstance(o, dict) else str(o)
        lines.append(f"{i}. {text}")
    return "\n".join(lines) or "（教案未提供目标列表）"


def _plan_blueprint(
    generator: Any,
    *,
    title: str,
    plan: Dict[str, Any],
    analysis: Dict[str, Any],
    slices: List[Dict[str, Any]],
    language_name: str,
    duration_minutes: int,
    course_type: str,
    teaching_intent: Optional[str],
) -> Tuple[List[Dict[str, Any]], str, str, str]:
    """阶段一：规划器一次调用出蓝图；未过校验带原因重试一次，仍失败确定性回退。
    返回 (pages, accent, source, note)，source ∈ {"llm", "fallback"}"""
    n_paras = len(slices)
    system_prompt, _ = render_prompt(PLANNER_PROMPT_NAME)
    _, user_prompt = render_prompt(
        PLANNER_PROMPT_NAME,
        title=_esc(title),
        language_name=_esc(language_name),
        duration_minutes=int(duration_minutes or 90),
        course_type=_esc(course_type or "综合"),
        n_paras=n_paras,
        para_range=f"{n_paras}~{n_paras * 2}",
        paragraphs_digest=_esc(_paragraphs_digest(slices)),
        plan_digest=_esc(_format_plan_text(plan)[:3000]),
        metrics_lines=_esc(_build_metrics_lines(analysis)),
        teacher_requirements=intent_prompt_section(teaching_intent),
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    reason = "规划器无输出"
    for _attempt in range(2):
        answer, _usage = generator._generate_with_api(messages)
        data = _extract_json_object(answer)
        pages, reason = _normalize_blueprint(data, n_paras)
        if pages is not None:
            return pages, str(data.get("accent", "")).lower(), "llm", ""
        logger.warning(f"课件蓝图校验失败（{reason}），重试一次")
        messages = messages + [
            {"role": "assistant", "content": answer[-1500:]},
            {"role": "user", "content": f"蓝图未通过程序校验：{reason}。请重新输出完整蓝图 JSON（精讲页覆盖全部 {n_paras} 个段落）。"},
        ]
    return _fallback_blueprint(slices), DEFAULT_ACCENT, "fallback", f"规划器两次未通过校验（{reason}），已用确定性蓝图"


def _page_spec_block(spec: Dict[str, Any], page_no: int, total: int) -> str:
    anchor = ""
    para = spec.get("para")
    if para:
        anchor = f"，锚定第 {para[0]}-{para[-1]} 段（共 {len(para)} 段）" if len(para) > 1 else f"，锚定第 {para[0]} 段"
    return (
        f"- 本页为全课件第 {page_no}/{total} 页\n"
        f"- 页型：{spec['kind']}（{KIND_LABELS.get(spec['kind'], '')}）{anchor}\n"
        f"- 页标题：{spec.get('title') or '（由你拟定）'}\n"
        f"- 教学意图：{spec.get('intent') or '（由你拟定一句可执行意图）'}"
    )


def _build_page_prompt(
    spec: Dict[str, Any],
    *,
    page_no: int,
    total: int,
    context_nav: str,
    paragraphs: List[str],
    slices: List[Dict[str, Any]],
    title: str,
    plan: Dict[str, Any],
    analysis: Dict[str, Any],
    text: str,
    language_name: str,
    text_level: str,
    student_level: str,
    duration_minutes: int,
    course_type: str,
    class_size: int,
    native_language: str,
    components: List[Dict[str, Any]],
    theme: Optional[CoursewareTheme] = None,
    teaching_intent: Optional[str] = None,
) -> str:
    cw_theme = theme or _ACADEMIC
    idxs = spec.get("para") or []
    para_block = "（本页无段落锚点）"
    slices_block = "-（本页无段落锚点）"
    if idxs:
        para_block = "\n\n".join(f"【第{i}段】\n{_esc(paragraphs[i - 1])}" for i in idxs)
        parts = []
        for s in (x for x in slices if x["index"] in idxs):
            words = "、".join(s["difficult_words"][:8]) or "（无）"
            sents = "\n  ".join(_esc(x) for x in s["long_sentences"]) or "（本段无超阈值长难句，可选次长句）"
            parts.append(f"- 第{s['index']}段 难点词：{words}\n  长难句候选：\n  {sents}")
        slices_block = "\n".join(parts)
    text_block = ""
    if spec["kind"] == "interaction":
        text_block = "### 课文全文（命题依据，答案必须可在课文找到依据）\n<user_content>\n" + _esc(prepare_text(text or ""))[:6000] + "\n</user_content>"
    _, user_prompt = render_prompt(
        PAGE_PROMPT_NAME,
        title=_esc(title),
        language_name=_esc(language_name),
        text_level=_esc(text_level),
        student_level=_esc(student_level),
        duration_minutes=int(duration_minutes or 90),
        course_type=_esc(course_type or "综合"),
        class_size=int(class_size or 30),
        native_language=_esc(native_language or "中文"),
        theme_desc=f"「{cw_theme.name}」主题（{cw_theme.palette_desc}）",
        teacher_requirements=intent_prompt_section(teaching_intent),
        page_spec=_page_spec_block(spec, page_no, total),
        context_nav=_esc(context_nav),
        para_block=para_block,
        slices_block=slices_block,
        paragraphs_digest=_esc(_paragraphs_digest(slices)),
        plan_digest=_esc(_format_plan_text(plan)[:3000]),
        objectives_digest=_esc(_objectives_digest(plan)),
        components_digest=_esc(_build_components_digest(components)),
        text_block=text_block,
    )
    return user_prompt


def _stub_page(spec: Dict[str, Any]) -> _ContentPage:
    """程序兜底页：LLM 完全无输出时保证整副不缺页"""
    title = spec.get("title") or KIND_LABELS.get(spec.get("kind", ""), "内容页")
    html = (
        '<div class="kicker">本页生成受限</div>'
        f"<h2>{_html_escape(title)}</h2>"
        '<div class="accent-rule"></div>'
        '<div class="page-focus"><p>本页由程序兜底生成，请在编辑器中补充内容。</p></div>'
    )
    return _ContentPage(title=title, intent=spec.get("intent") or "程序兜底页", html=html)


def _generate_one_page(
    generator: Any,
    system_prompt: str,
    spec: Dict[str, Any],
    prompt_kwargs: Dict[str, Any],
    page_no: int,
    total: int,
    context_nav: str,
) -> Tuple[_ContentPage, Dict[str, Any]]:
    """单页生成 + 程序自检 + 定向重生成 ≤2 轮 + 确定性净化 + 程序兜底"""
    info: Dict[str, Any] = {"regens": 0, "sanitized": False, "stub": False}
    user_prompt = _build_page_prompt(spec, page_no=page_no, total=total, context_nav=context_nav, **prompt_kwargs)
    try:
        answer, _usage = generator._generate_with_api([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        _, pages = _parse_pages(answer)
        page = pages[0] if len(pages) == 1 else None
        if page is not None:
            page.title = page.title or spec.get("title") or ""
            # 蓝图意图是权威任务描述（S4 教师可编辑），LLM 页内注释只是复述
            page.intent = spec.get("intent") or page.intent or ""
            problems = _validate_content_page(page)
        else:
            problems = ["输出未包含恰好一个 ```html 页面块"]
        for _round in range(2):
            if not problems:
                break
            info["regens"] += 1
            fixed = _regen_page(generator, system_prompt, user_prompt, page or _stub_page(spec), page_no, problems)
            if fixed is None:
                break
            page = fixed
            page.title = page.title or spec.get("title") or ""
            page.intent = spec.get("intent") or page.intent or ""
            problems = _validate_content_page(page)
        if problems and page is not None:
            page.html = _sanitize_page(page.html)
            info["sanitized"] = True
        if page is None:
            page = _stub_page(spec)
            info["stub"] = True
        return page, info
    except Exception as e:
        logger.warning(f"课件第 {page_no} 页生成异常，程序兜底: {e}")
        return _stub_page(spec), {"regens": 0, "sanitized": False, "stub": True}


def _generate_pages(
    generator: Any,
    blueprint: List[Dict[str, Any]],
    prompt_kwargs: Dict[str, Any],
    progress_cb: Optional[Callable[[str], None]] = None,
) -> Tuple[List[_ContentPage], Dict[int, Dict[str, Any]]]:
    """阶段二：蓝图逐页生成，3 路有限并发；进度文案含页类型（微调 c）"""
    system_prompt, _ = render_prompt(PAGE_PROMPT_NAME)
    total = len(blueprint)
    results: Dict[int, _ContentPage] = {}
    infos: Dict[int, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {}
        for i, spec in enumerate(blueprint):
            prev_t = (blueprint[i - 1].get("title") or KIND_LABELS.get(blueprint[i - 1]["kind"], "未知")) if i else "（无）"
            next_t = (blueprint[i + 1].get("title") or KIND_LABELS.get(blueprint[i + 1]["kind"], "未知")) if i + 1 < total else "（无）"
            context_nav = f"前一页「{prev_t}」，后一页「{next_t}」"
            futures[pool.submit(_generate_one_page, generator, system_prompt, spec, prompt_kwargs, i + 1, total, context_nav)] = i
        for fut in as_completed(futures):
            i = futures[fut]
            page, info = fut.result()
            results[i] = page
            infos[i] = info
            if progress_cb:
                progress_cb(f"正在生成：{_page_progress_label(blueprint[i])}（{i + 1}/{total}）")
    return [results[i] for i in range(total)], infos


def _wrap_llm_schema(title: str, html: str, source_meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """LLM 产物的编辑器 schema：单页 html_embed，编辑器渲染时收编 rendered_html"""
    page_id = f"page-{uuid4().hex[:8]}"
    return {
        "meta": {
            "title": title,
            "mode": "slides",
            "template_id": "classroom_default",
            "source_type": "from_plan_llm",
            "created_at": datetime.utcnow().isoformat(),
            "source_meta": source_meta or {},
        },
        "outline": [{"id": page_id, "label": "AI 生成课件", "source_key": "rendered_html"}],
        "pages": [
            {
                "id": page_id,
                "kind": "slide",
                "title": title,
                "blocks": [
                    {
                        "id": f"block-{uuid4().hex[:8]}",
                        "type": "html_embed",
                        "label": "AI 生成内容",
                        "editable": "free",
                        "source_key": "rendered_html",
                        "content": {"html": html},
                    }
                ],
            }
        ],
    }


def _structure_sync_from_pages(schema: Dict[str, Any]) -> Dict[str, Any]:
    pages = []
    for page in schema.get("pages", []):
        pages.append(
            {
                "page_id": page.get("id"),
                "page_title": page.get("title"),
                "blocks": [
                    {
                        "block_id": b.get("id"),
                        "source_key": b.get("source_key"),
                        "editable": b.get("editable"),
                        "type": b.get("type"),
                    }
                    for b in page.get("blocks", [])
                ],
            }
        )
    return {"pages": pages}


def generate_html_courseware(
    *,
    title: str,
    plan: Dict[str, Any],
    analysis: Dict[str, Any],
    text: str,
    language_name: str = "英语",
    text_level: str = "",
    student_level: str = "",
    duration_minutes: int = 90,
    course_type: Optional[str] = None,
    class_size: Optional[int] = None,
    native_language: Optional[str] = None,
    components: Optional[List[Dict[str, Any]]] = None,
    learner_gap: Optional[Dict[str, Any]] = None,
    enhancement_tags: Optional[List[str]] = None,
    theme: Optional[str] = None,
    teaching_intent: Optional[str] = None,
    blueprint: Optional[List[Dict[str, Any]]] = None,
    accent: Optional[str] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> HTMLCoursewareResult:
    """
    生成单文件交互 HTML 课件（③ 两阶段 + ④a 三层架构）。

    阶段一 规划器：LLM 一次调用产出页面蓝图（页型/标题/意图/段落锚点/强调色），
    程序硬校验（页型合法 + 段落全覆盖 + ≤25 页截断），失败带原因重试一次，
    仍失败确定性回退蓝图。教师传入已确认蓝图时（S4）跳过规划器直接采用
    （同样过校验，未过则带原因回退内部规划）。阶段二 逐页生成：按蓝图 3 路并发，每页带段落原文与
    白盒切片；逐页程序自检，不合格定向重生成 ≤2 轮，仍失败确定性净化，完全
    无输出用程序兜底页，整副不缺页。任意阶段异常回退 courseware_bootstrap，
    fallback=True 由前端标注"简化版生成"，绝不静默。
    """
    start_time = time.time()
    version = prompt_version(PAGE_PROMPT_NAME)
    components = components or []
    cw_theme = get_theme(theme)

    model_name = "template-fallback"
    fallback_used = True
    retries = 0
    html = ""
    accent = accent or DEFAULT_ACCENT
    pages: List[_ContentPage] = []
    blueprint = list(blueprint) if blueprint else []
    blueprint_source = ""
    blueprint_note: Optional[str] = None
    self_check: Dict[str, Any] = {}

    def _progress(msg: str) -> None:
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    try:
        from app.services.rag import RAGGenerator
        from app.core.config import settings

        model_name = getattr(settings, "LLM_MODEL", "deepseek-chat")
        generator = RAGGenerator(
            api_key=getattr(settings, "LLM_API_KEY", None),
            api_base=getattr(settings, "LLM_BASE_URL", None),
            model=model_name,
            max_tokens=4000,
            temperature=0.7,
        )

        if generator.use_api:
            paragraphs = _split_paragraphs(text)
            slices = _slice_analysis(paragraphs, analysis)
            teacher_note = ""
            if blueprint:
                normalized, reject = _normalize_blueprint({"pages": blueprint}, len(paragraphs))
                if normalized is None:
                    teacher_note = f"教师蓝图未过校验（{reject}），已改用内部规划"
                    logger.warning(teacher_note)
                    blueprint = []
                else:
                    blueprint = normalized
            if blueprint:
                # S4 蓝图可编辑：教师已确认，跳过内部规划直接逐页生成
                blueprint_source = "teacher"
                _progress(f"已采用教师确认蓝图（{len(blueprint)} 页），开始逐页生成…")
            else:
                _progress("正在规划课件页面结构…")
                blueprint, accent, blueprint_source, planner_note = _plan_blueprint(
                    generator,
                    title=title,
                    plan=plan,
                    analysis=analysis or {},
                    slices=slices,
                    language_name=language_name,
                    duration_minutes=duration_minutes,
                    course_type=course_type or "综合",
                    teaching_intent=teaching_intent,
                )
                notes = [n for n in (teacher_note, planner_note) if n]
                blueprint_note = "；".join(notes) or None
            retries = 1 if blueprint_source == "fallback" else 0
            if blueprint_source != "teacher":
                _progress(
                    f"页面蓝图完成（{len(blueprint)} 页，{'AI 规划' if blueprint_source == 'llm' else '模板规划'}），开始逐页生成…"
                )
            prompt_kwargs = dict(
                paragraphs=paragraphs,
                slices=slices,
                title=title,
                plan=plan,
                analysis=analysis or {},
                text=text,
                language_name=language_name,
                text_level=text_level or "",
                student_level=student_level or "",
                duration_minutes=duration_minutes,
                course_type=course_type or "综合",
                class_size=class_size or 30,
                native_language=native_language or "中文",
                components=components,
                theme=cw_theme,
                teaching_intent=teaching_intent,
            )
            pages, page_infos = _generate_pages(generator, blueprint, prompt_kwargs, _progress)

            # S5 教研员评审：逐页复核，fail 带意见重写 ≤2 轮；异常保留原稿不阻塞产出
            reviewer_summary: Optional[Dict[str, Any]] = None
            if getattr(settings, "PAGE_REVIEWER_ENABLED", True):
                _progress("AI 教研员正在复核页面质量…")
                try:
                    from app.services.courseware_page_reviewer import review_pages

                    pages, reviewer_summary = review_pages(
                        generator, blueprint, prompt_kwargs, pages, page_infos, _progress
                    )
                except Exception as rev_e:
                    logger.warning(f"教研员复核整体异常，跳过复核: {rev_e}")

            fallback_used = False
            accent_note = None
            if cw_theme.dark:
                # 深色主题：全局色板为浅底调色，对其底色不达对比度契约，锁定主题专属强调色
                if accent and accent != cw_theme.default_accent:
                    accent_note = f"深色主题强调色锁定 {cw_theme.default_accent}（规划器声明 {accent} 已忽略）"
                accent = cw_theme.default_accent
            elif accent not in ACCENT_PALETTE:
                logger.warning(f"强调色 {accent or '未声明'} 不在色板内，回退默认 {DEFAULT_ACCENT}")
                accent_note = f"声明值 {accent or '未声明'} 不在色板，已用默认 {DEFAULT_ACCENT}"
                accent = DEFAULT_ACCENT

            # S6 视觉质检（两相）：溢出硬关卡（OVERFLOW_GATE_ENABLED，本地几何）+ VL 检查（VISUAL_QC_ENABLED）
            visual_qc_summary: Optional[Dict[str, Any]] = None
            _vl_on = getattr(settings, "VISUAL_QC_ENABLED", True)
            _gate_on = getattr(settings, "OVERFLOW_GATE_ENABLED", True)
            if _vl_on or _gate_on:
                try:
                    from app.services.courseware_visual_qc import run_visual_qc

                    def _make_doc(pg: _ContentPage) -> str:
                        return _assemble_skeleton(title, accent, [pg], theme=cw_theme)

                    def _regen_for_visual(i: int, pg: _ContentPage, problems: List[str]) -> Optional[_ContentPage]:
                        spec = blueprint[i]
                        prev_t = (blueprint[i - 1].get("title") or KIND_LABELS.get(blueprint[i - 1]["kind"], "未知")) if i else "（无）"
                        next_t = (blueprint[i + 1].get("title") or KIND_LABELS.get(blueprint[i + 1]["kind"], "未知")) if i + 1 < len(blueprint) else "（无）"
                        page_system, _ = render_prompt(PAGE_PROMPT_NAME)
                        page_prompt = _build_page_prompt(
                            spec, page_no=i + 1, total=len(blueprint),
                            context_nav=f"前一页「{prev_t}」，后一页「{next_t}」", **prompt_kwargs,
                        )
                        rewritten = _regen_page(generator, page_system, page_prompt, pg, i + 1, problems)
                        if rewritten is not None:
                            rewritten.title = rewritten.title or spec.get("title") or ""
                            rewritten.intent = spec.get("intent") or rewritten.intent
                        return rewritten

                    pages, visual_qc_summary = run_visual_qc(
                        pages,
                        blueprint=blueprint,
                        make_doc=_make_doc,
                        regen_page=_regen_for_visual,
                        kind_labels=KIND_LABELS,
                        progress_cb=_progress,
                        vl_enabled=_vl_on,
                        gate_enabled=_gate_on,
                    )
                except Exception as qc_e:
                    logger.warning(f"视觉质检整体异常，跳过: {qc_e}")
                    visual_qc_summary = {"enabled": True, "error": str(qc_e)[:200]}
            else:
                logger.info("视觉质检环节跳过：VISUAL_QC_ENABLED 与 OVERFLOW_GATE_ENABLED 均为 false")
            self_check = {
                "prompt_version": version,
                "planner_version": prompt_version(PLANNER_PROMPT_NAME),
                "generation_mode": "two_stage",
                "accent": accent,
                "accent_note": accent_note,
                "theme": cw_theme.id,
                "pages_count": len(pages),
                "blueprint": {
                    "source": blueprint_source,
                    "note": blueprint_note or None,
                    "pages": [
                        {"page": i + 1, "kind": spec["kind"], "para": spec.get("para"), "title": spec.get("title")}
                        for i, spec in enumerate(blueprint)
                    ],
                },
                "page_intents": [
                    {"page": i + 1, "title": p.title, "intent": p.intent} for i, p in enumerate(pages)
                ],
                "interaction_types": sorted(_interaction_types(pages)),
                "regenerated_pages": [i + 1 for i in sorted(page_infos) if page_infos[i]["regens"]],
                "sanitized_pages": [i + 1 for i in sorted(page_infos) if page_infos[i]["sanitized"]],
                "stub_pages": [i + 1 for i in sorted(page_infos) if page_infos[i]["stub"]],
                "reviewer": reviewer_summary if reviewer_summary is not None else {"enabled": False},
                "visual_qc": visual_qc_summary if visual_qc_summary is not None else {"enabled": False},
            }
        else:
            logger.warning("LLM 不可用，HTML 课件回退模板拼装")
    except Exception as e:
        logger.warning(f"HTML 课件 LLM 生成失败，回退模板拼装: {e}")

    if fallback_used:
        from app.services.courseware_bootstrap import build_courseware_from_plan

        bootstrap = build_courseware_from_plan(
            title=title,
            mode="slides",
            template_id="classroom_default",
            plan=plan,
            learner_gap=learner_gap,
            enhancement_tags=enhancement_tags,
            components=components,
        )
        html = bootstrap["rendered_html"]
        schema = bootstrap["editor_schema_json"]
        sync = bootstrap["structure_sync_json"]
        self_check = {
            "prompt_version": "fallback",
            "notes": "LLM 生成不可用或未通过校验，已用教案模板拼装（简化版生成）",
        }
        source_meta = {"generated_by": "template_fallback", "prompt_version": version}
    else:
        html = _assemble_skeleton(title, accent, pages, theme=cw_theme)
        # S7 全局一致性审校：术语统一（文本节点替换 + 结构校验回滚）+ 结构意见存 meta
        consistency_summary: Optional[Dict[str, Any]] = None
        from app.core.config import settings as _cons_settings

        if getattr(_cons_settings, "CONSISTENCY_REVIEW_ENABLED", True):
            try:
                from app.services.courseware_consistency import run_consistency_review

                _progress("AI 正在做全局一致性审校…")
                html, consistency_summary = run_consistency_review(
                    generator,
                    html=html,
                    title=title,
                    language_name=language_name,
                    student_level=student_level or "",
                    progress_cb=_progress,
                )
            except Exception as cons_e:
                logger.warning(f"全局一致性审校异常，跳过: {cons_e}")
                consistency_summary = {"enabled": True, "error": str(cons_e)[:200]}
        self_check["consistency_review"] = consistency_summary if consistency_summary is not None else {"enabled": False}
        source_meta = {
            "generated_by": "llm_html_two_stage",
            "prompt_version": version,
            "theme": cw_theme.id,
            "page_blueprint": blueprint,
            "consistency_review": consistency_summary,
        }
        schema = _wrap_llm_schema(title, html, source_meta)
        sync = _structure_sync_from_pages(schema)

    return HTMLCoursewareResult(
        html=html,
        editor_schema=schema,
        structure_sync=sync,
        self_check=self_check,
        prompt_version=version,
        model=model_name if not fallback_used else "template-fallback",
        fallback=fallback_used,
        retries=retries,
        generation_duration=round(time.time() - start_time, 2),
    )


# ============ F3.3 PPT 链路 ============

PPT_PROMPT_NAME = "courseware_ppt_v1"

_PPT_KINDS = {"cover", "agenda", "content", "quote", "interaction", "vocab", "summary"}

# Morandi 平台色（与前端 tokens 同源）
_PPT_INK = "3A3A37"
_PPT_INK_SOFT = "6B6B66"
_PPT_SAGE = "96A790"
_PPT_SAGE_DARK = "767870"
_PPT_ACCENT = "D8C46A"
_PPT_CANVAS = "FAF9F6"
_PPT_ROSE_LIGHT = "EFE7E2"


@dataclass
class PPTCoursewareResult:
    outline: Dict[str, Any]
    pptx_bytes: BytesIO
    slide_count: int
    self_check: Dict[str, Any] = field(default_factory=dict)
    prompt_version: str = ""
    model: str = ""
    fallback: bool = False
    retries: int = 0
    generation_duration: float = 0.0


def _extract_json_object(answer: str) -> Dict[str, Any]:
    """提取 ```json 代码块；无围栏时退而取首个平衡的 {...} 片段"""
    blocks = re.findall(r"```json\s*(.*?)\s*```", answer, re.DOTALL | re.IGNORECASE)
    for block in blocks:
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue
    depth = 0
    start = -1
    for i, ch in enumerate(answer):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(answer[start : i + 1])
                except json.JSONDecodeError:
                    start = -1
    return {}


def _validate_ppt_outline(outline: Dict[str, Any], min_slides: int) -> Optional[str]:
    """返回 None 表示通过，否则返回失败原因（用于重试反馈与回退判定）"""
    slides = outline.get("slides")
    if not isinstance(slides, list) or len(slides) < min_slides:
        actual = len(slides) if isinstance(slides, list) else 0
        return f"页数不足：需 ≥{min_slides} 页（环节数+3），实际 {actual}"
    problems = []
    for i, s in enumerate(slides, 1):
        if not isinstance(s, dict):
            problems.append(f"第{i}页不是对象")
            continue
        if not str(s.get("title", "")).strip():
            problems.append(f"第{i}页缺标题")
        bullets = s.get("bullets")
        if not isinstance(bullets, list) or not bullets:
            problems.append(f"第{i}页无要点")
        elif len(bullets) > 6:
            problems.append(f"第{i}页要点 {len(bullets)} 条，超过 6 条上限")
        if len(str(s.get("notes", "")).strip()) < 20:
            problems.append(f"第{i}页讲者备注过短")
    if problems:
        return "；".join(problems[:5])
    return None


def _build_ppt_prompt(
    *,
    title: str,
    plan: Dict[str, Any],
    analysis: Dict[str, Any],
    text: str,
    language_name: str,
    text_level: str,
    student_level: str,
    duration_minutes: int,
    course_type: str,
    class_size: int,
    native_language: str,
    slide_count_hint: int,
    teaching_intent: Optional[str] = None,
) -> str:
    _, user_prompt = render_prompt(
        PPT_PROMPT_NAME,
        title=_esc(title),
        language_name=_esc(language_name),
        text_level=_esc(text_level),
        student_level=_esc(student_level),
        duration_minutes=int(duration_minutes or 90),
        course_type=_esc(course_type or "综合"),
        class_size=int(class_size or 30),
        native_language=_esc(native_language or "中文"),
        slide_count_hint=int(slide_count_hint),
        full_text=_esc(prepare_text(text or "")),
        plan_text=_esc(_format_plan_text(plan)),
        metrics_lines=_esc(_build_metrics_lines(analysis)),
        teacher_requirements=intent_prompt_section(teaching_intent),
    )
    return user_prompt


def _fallback_ppt_outline(title: str, plan: Dict[str, Any], language_name: str, duration_minutes: int) -> Dict[str, Any]:
    """LLM 不可用时的确定性大纲：封面/目标/逐环节/总结，notes 标注模板生成"""
    slides: List[Dict[str, Any]] = [
        {
            "kind": "cover",
            "title": title,
            "bullets": [f"{language_name} · 课堂课件", f"课时 {duration_minutes or 90} 分钟"],
            "notes": "封面页。开场问候后快速过页，报出本课主题与课时安排。（模板生成：AI 大纲暂不可用，可生成后人工调整）",
            "layout_hint": "center",
        }
    ]
    objectives = plan.get("objectives") or []
    if objectives:
        slides.append({
            "kind": "agenda",
            "title": "教学目标",
            "bullets": [str(o.get("text", o) if isinstance(o, dict) else o)[:40] for o in objectives[:6]],
            "notes": "目标页。逐条口头展开，强调本课结束时学生能做到什么。（模板生成）",
            "layout_hint": "bullets",
        })
    for i, act in enumerate(plan.get("activity_designs") or [], 1):
        if not isinstance(act, dict):
            continue
        bullets: List[str] = []
        if act.get("objective"):
            bullets.append(str(act["objective"])[:40])
        if act.get("steps"):
            steps = re.split(r"[；;。]", str(act["steps"]))
            bullets += [s.strip()[:30] for s in steps if s.strip()][:4]
        slides.append({
            "kind": "content",
            "title": f"{act.get('name', f'环节{i}')[:15]}",
            "bullets": bullets[:6] or ["（本环节要点待补充）"],
            "notes": f"本环节约 {act.get('duration', '—')}。{act.get('assessment') or act.get('objective') or ''}（模板生成）"[:200],
            "layout_hint": "bullets",
        })
    slides.append({
        "kind": "summary",
        "title": "总结与作业",
        "bullets": [str(s)[:30] for s in (plan.get("assessment", {}) or {}).get("summative", [])][:5] or ["回顾本课要点"],
        "notes": "总结页。回收本课目标达成情况并布置作业。（模板生成）",
        "layout_hint": "bullets",
    })
    return {"slides": slides, "self_check": {"source": "template_fallback"}}


def _render_pptx(outline: Dict[str, Any], title: str) -> BytesIO:
    """把大纲 JSON 渲染为 16:9 .pptx（Morandi 版式，讲者备注入 notes）"""
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    def rgb(hexstr: str) -> "RGBColor":
        return RGBColor(int(hexstr[0:2], 16), int(hexstr[2:4], 16), int(hexstr[4:6], 16))

    ink, ink_soft = rgb(_PPT_INK), rgb(_PPT_INK_SOFT)
    sage, sage_dark, accent = rgb(_PPT_SAGE), rgb(_PPT_SAGE_DARK), rgb(_PPT_ACCENT)
    canvas, rose_light = rgb(_PPT_CANVAS), rgb(_PPT_ROSE_LIGHT)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    def fill_bg(slide, color) -> None:
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = color

    def add_rect(slide, x, y, w, h, color) -> None:
        from pptx.enum.shapes import MSO_SHAPE

        shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        shp.fill.solid()
        shp.fill.fore_color.rgb = color
        shp.line.fill.background()

    def add_text(slide, x, y, w, h, lines, size, color, *, bold=False, italic=False, align=PP_ALIGN.LEFT, space_after=10):
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.word_wrap = True
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = str(line)
            p.alignment = align
            p.space_after = Pt(space_after)
            for run in p.runs:
                run.font.size = Pt(size)
                run.font.color.rgb = color
                run.font.bold = bold
                run.font.italic = italic
        return box

    slides = outline.get("slides", [])
    total = max(len(slides), 1)
    for idx, s in enumerate(slides, 1):
        slide = prs.slides.add_slide(blank)
        kind = s.get("kind") if s.get("kind") in _PPT_KINDS else "content"
        bullets = [str(b) for b in (s.get("bullets") or [])][:6]
        hint = s.get("layout_hint")
        title_text = str(s.get("title", "")).strip() or "—"
        center = kind in {"cover", "quote", "interaction"} or hint == "center"

        if kind == "interaction":
            fill_bg(slide, rose_light)
            add_text(slide, 1.0, 1.6, 11.3, 1.2, [title_text], 30, ink, bold=True, align=PP_ALIGN.CENTER)
            add_text(slide, 1.5, 3.1, 10.3, 3.4, bullets, 20, ink_soft, align=PP_ALIGN.CENTER, space_after=14)
        elif kind == "quote":
            fill_bg(slide, canvas)
            add_rect(slide, 0, 0, 13.333, 0.12, sage)
            add_text(slide, 1.0, 0.8, 11.3, 0.8, [title_text], 14, sage_dark, align=PP_ALIGN.CENTER)
            add_text(slide, 1.8, 2.4, 9.7, 3.6, ["“ " + b + " ”" for b in bullets] or ["…"], 22, ink_soft, italic=True, align=PP_ALIGN.CENTER, space_after=16)
        elif kind == "cover":
            fill_bg(slide, canvas)
            add_rect(slide, 0, 6.9, 13.333, 0.6, sage)
            add_text(slide, 1.0, 2.4, 11.3, 1.6, [title_text], 36, ink, bold=True, align=PP_ALIGN.CENTER)
            add_text(slide, 1.0, 4.2, 11.3, 1.6, bullets, 16, ink_soft, align=PP_ALIGN.CENTER, space_after=8)
        else:
            fill_bg(slide, canvas)
            add_rect(slide, 0, 0, 13.333, 0.12, sage)
            add_text(slide, 0.8, 0.5, 11.7, 1.0, [title_text], 24, ink, bold=True)
            add_rect(slide, 0.85, 1.45, 1.2, 0.06, accent)
            if hint == "two_col" and len(bullets) >= 4:
                half = (len(bullets) + 1) // 2
                add_text(slide, 0.8, 2.0, 5.7, 4.6, bullets[:half], 18, ink_soft, space_after=12)
                add_text(slide, 6.9, 2.0, 5.7, 4.6, bullets[half:], 18, ink_soft, space_after=12)
            else:
                add_text(slide, 0.8, 2.0, 11.7, 4.6, bullets, 18, ink_soft, space_after=12)

        notes = str(s.get("notes", "")).strip()
        if notes:
            slide.notes_slide.notes_text_frame.text = notes

        add_text(slide, 0.8, 7.05, 8.0, 0.4, [title[:40]], 9, ink_soft)
        add_text(slide, 11.5, 7.05, 1.4, 0.4, [f"{idx} / {total}"], 9, ink_soft, align=PP_ALIGN.RIGHT)

    # AIGC 标识末页（合规要求：AI 生成内容显式标识）
    slide = prs.slides.add_slide(blank)
    fill_bg(slide, canvas)
    add_text(slide, 1.0, 2.9, 11.3, 1.2, ["本课件由 OutEye Edu AI 生成"], 24, ink_soft, align=PP_ALIGN.CENTER)
    add_text(slide, 1.0, 4.2, 11.3, 0.8, ["仅供教学参考，请教师核对后使用"], 14, ink_soft, align=PP_ALIGN.CENTER)

    buf = BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf


def generate_ppt_courseware(
    *,
    title: str,
    plan: Dict[str, Any],
    analysis: Dict[str, Any],
    text: str,
    language_name: str = "英语",
    text_level: str = "",
    student_level: str = "",
    duration_minutes: int = 90,
    course_type: Optional[str] = None,
    class_size: Optional[int] = None,
    native_language: Optional[str] = None,
    teaching_intent: Optional[str] = None,
) -> PPTCoursewareResult:
    """
    生成 16:9 课堂放映 PPT：LLM 逐页大纲 JSON → python-pptx 渲染。
    大纲校验失败自动重试一次（携带原因）；仍失败回退确定性大纲，fallback=True。
    """
    start_time = time.time()
    version = prompt_version(PPT_PROMPT_NAME)
    activities = plan.get("activity_designs") or []
    min_slides = max(5, len(activities) + 3)
    slide_count_hint = len(activities) + 4

    model_name = "template-fallback"
    fallback_used = True
    retries = 0
    outline: Dict[str, Any] = {}
    self_check: Dict[str, Any] = {}
    raw_answer = ""

    try:
        user_prompt = _build_ppt_prompt(
            title=title,
            plan=plan,
            analysis=analysis or {},
            text=text,
            language_name=language_name,
            text_level=text_level,
            student_level=student_level,
            duration_minutes=duration_minutes,
            course_type=course_type or "综合",
            class_size=class_size or 30,
            native_language=native_language or "中文",
            slide_count_hint=slide_count_hint,
            teaching_intent=teaching_intent,
        )

        from app.services.rag import RAGGenerator
        from app.core.config import settings

        model_name = getattr(settings, "LLM_MODEL", "deepseek-chat")
        generator = RAGGenerator(
            api_key=getattr(settings, "LLM_API_KEY", None),
            api_base=getattr(settings, "LLM_BASE_URL", None),
            model=model_name,
            max_tokens=6000,
            temperature=0.6,
        )

        if generator.use_api:
            system_prompt, _ = render_prompt(PPT_PROMPT_NAME)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            answer, _usage = generator._generate_with_api(messages)
            raw_answer = answer
            outline = _extract_json_object(answer)
            reason = _validate_ppt_outline(outline, min_slides)

            if reason:
                retries = 1
                logger.warning(f"PPT 大纲首次校验失败（{reason}），重试一次")
                messages += [
                    {"role": "assistant", "content": answer[-2000:]},
                    {"role": "user", "content": f"上一次输出未通过结构校验：{reason}。请重新输出完整的大纲 JSON，严格遵循输出契约。"},
                ]
                answer, _usage = generator._generate_with_api(messages)
                raw_answer = answer
                outline = _extract_json_object(answer)
                reason = _validate_ppt_outline(outline, min_slides)

            if reason:
                logger.warning(f"PPT 大纲重试仍失败（{reason}），回退确定性大纲")
            else:
                fallback_used = False
                self_check = outline.get("self_check") or {}
        else:
            logger.warning("LLM 不可用，PPT 回退确定性大纲")
    except Exception as e:
        logger.warning(f"PPT 课件 LLM 生成失败，回退确定性大纲: {e}")

    if fallback_used:
        outline = _fallback_ppt_outline(title, plan, language_name, duration_minutes)
        self_check = {"prompt_version": "fallback", "notes": "LLM 大纲不可用或未通过校验，已用教案确定性大纲渲染（简化版生成）"}

    pptx_bytes = _render_pptx(outline, title)
    return PPTCoursewareResult(
        outline=outline,
        pptx_bytes=pptx_bytes,
        slide_count=len(outline.get("slides", [])),
        self_check=self_check,
        prompt_version=version,
        model=model_name if not fallback_used else "template-fallback",
        fallback=fallback_used,
        retries=retries,
        generation_duration=round(time.time() - start_time, 2),
    )


# ============ F3.4 Word 链路 ============

WORD_PROMPT_NAME = "courseware_word_v1"

_WORD_KINDS = {"cover", "objectives", "stage", "board", "homework", "appendix"}


@dataclass
class WordCoursewareResult:
    outline: Dict[str, Any]
    docx_bytes: BytesIO
    section_count: int
    self_check: Dict[str, Any] = field(default_factory=dict)
    prompt_version: str = ""
    model: str = ""
    fallback: bool = False
    retries: int = 0
    generation_duration: float = 0.0


def _validate_word_outline(outline: Dict[str, Any], min_sections: int) -> Optional[str]:
    """返回 None 表示通过，否则返回失败原因（用于重试反馈与回退判定）"""
    sections = outline.get("sections")
    if not isinstance(sections, list) or len(sections) < min_sections:
        actual = len(sections) if isinstance(sections, list) else 0
        return f"章节数不足：需 ≥{min_sections} 节（环节数+3），实际 {actual}"
    problems = []
    for i, s in enumerate(sections, 1):
        if not isinstance(s, dict):
            problems.append(f"第{i}节不是对象")
            continue
        if not str(s.get("heading", "")).strip():
            problems.append(f"第{i}节缺标题")
        has_content = bool(s.get("bullets") or s.get("paragraphs") or s.get("table"))
        if not has_content:
            problems.append(f"第{i}节无内容（bullets/paragraphs/table 至少一项）")
    if problems:
        return "；".join(problems[:5])
    return None


def _build_word_prompt(
    *,
    title: str,
    plan: Dict[str, Any],
    analysis: Dict[str, Any],
    text: str,
    language_name: str,
    text_level: str,
    student_level: str,
    duration_minutes: int,
    course_type: str,
    class_size: int,
    native_language: str,
    teaching_intent: Optional[str] = None,
) -> str:
    _, user_prompt = render_prompt(
        WORD_PROMPT_NAME,
        title=_esc(title),
        language_name=_esc(language_name),
        text_level=_esc(text_level),
        student_level=_esc(student_level),
        duration_minutes=int(duration_minutes or 90),
        course_type=_esc(course_type or "综合"),
        class_size=int(class_size or 30),
        native_language=_esc(native_language or "中文"),
        full_text=_esc(prepare_text(text or "")),
        plan_text=_esc(_format_plan_text(plan)),
        metrics_lines=_esc(_build_metrics_lines(analysis)),
        teacher_requirements=intent_prompt_section(teaching_intent),
    )
    return user_prompt


def _fallback_word_outline(title: str, plan: Dict[str, Any], language_name: str, duration_minutes: int) -> Dict[str, Any]:
    """LLM 不可用时的确定性文档结构：封面/目标/逐环节/板书/作业"""
    sections: List[Dict[str, Any]] = [
        {
            "kind": "cover",
            "heading": title,
            "bullets": [f"语种：{language_name}", f"课时：{duration_minutes or 90} 分钟"],
            "paragraphs": ["（模板生成：AI 文档结构暂不可用，以下为教案确定性文档，可人工调整。）"],
        },
        {
            "kind": "objectives",
            "heading": "教学目标",
            "bullets": [str(o.get("text", o) if isinstance(o, dict) else o) for o in (plan.get("objectives") or [])][:8],
            "paragraphs": [],
        },
    ]
    board_lines = []
    for i, act in enumerate(plan.get("activity_designs") or [], 1):
        if not isinstance(act, dict):
            continue
        steps = re.split(r"[；;]", str(act.get("steps", "")))
        step_lines = [f"步骤{j}：{s.strip()}" for j, s in enumerate(steps, 1) if s.strip()]
        sections.append({
            "kind": "stage",
            "heading": f"环节{i} {act.get('name', '')}（{act.get('duration', '—')}）",
            "bullets": ([f"目标：{act['objective']}"] if act.get("objective") else [])
                       + ([f"评估点：{act['assessment']}"] if act.get("assessment") else []),
            "paragraphs": step_lines or ["（步骤待补充）"],
        })
        board_lines.append(f"环节{i} {act.get('name', '')}：{act.get('objective', '')}")
    sections.append({
        "kind": "board",
        "heading": "板书设计",
        "bullets": board_lines or ["（板书待设计）"],
        "paragraphs": [],
    })
    sections.append({
        "kind": "homework",
        "heading": "作业与课后评估",
        "bullets": [str(s) for s in (plan.get("assessment", {}) or {}).get("summative", [])] or ["（作业待布置）"],
        "paragraphs": [],
    })
    return {"sections": sections, "self_check": {"source": "template_fallback"}}


def _render_docx(outline: Dict[str, Any], title: str) -> BytesIO:
    """把文档结构 JSON 渲染为 .docx（封面 + 逐节标题/条目/段落/表格）"""
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    doc.add_heading(title, 0)

    for s in outline.get("sections", []):
        kind = s.get("kind") if s.get("kind") in _WORD_KINDS else "stage"
        heading = str(s.get("heading", "")).strip()
        if kind != "cover" and heading:
            doc.add_heading(heading, level=1)
        for para in s.get("paragraphs") or []:
            doc.add_paragraph(str(para))
        for bullet in s.get("bullets") or []:
            doc.add_paragraph(str(bullet), style="List Bullet")
        table = s.get("table")
        if isinstance(table, dict) and isinstance(table.get("headers"), list):
            headers = [str(h) for h in table["headers"]]
            rows = [[str(c) for c in row] for row in (table.get("rows") or [])]
            t = doc.add_table(rows=1, cols=len(headers))
            t.style = "Table Grid"
            for j, h in enumerate(headers):
                cell = t.rows[0].cells[j]
                cell.text = h
                for run in cell.paragraphs[0].runs:
                    run.font.bold = True
            for row in rows:
                cells = t.add_row().cells
                for j, val in enumerate(row[: len(headers)]):
                    cells[j].text = val

    # AIGC 标识末段（合规要求：AI 生成内容显式标识）
    p = doc.add_paragraph("本文档由 OutEye Edu AI 生成，仅供教学参考，请教师核对后使用。")
    for run in p.runs:
        run.font.size = Pt(9)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def generate_word_courseware(
    *,
    title: str,
    plan: Dict[str, Any],
    analysis: Dict[str, Any],
    text: str,
    language_name: str = "英语",
    text_level: str = "",
    student_level: str = "",
    duration_minutes: int = 90,
    course_type: Optional[str] = None,
    class_size: Optional[int] = None,
    native_language: Optional[str] = None,
    teaching_intent: Optional[str] = None,
) -> WordCoursewareResult:
    """
    生成教师课堂执行文档（Word）：LLM 结构 JSON → python-docx 渲染。
    校验失败自动重试一次；仍失败回退确定性结构，fallback=True。
    """
    start_time = time.time()
    version = prompt_version(WORD_PROMPT_NAME)
    activities = plan.get("activity_designs") or []
    min_sections = len(activities) + 3

    model_name = "template-fallback"
    fallback_used = True
    retries = 0
    outline: Dict[str, Any] = {}
    self_check: Dict[str, Any] = {}
    raw_answer = ""

    try:
        user_prompt = _build_word_prompt(
            title=title,
            plan=plan,
            analysis=analysis or {},
            text=text,
            language_name=language_name,
            text_level=text_level,
            student_level=student_level,
            duration_minutes=duration_minutes,
            course_type=course_type or "综合",
            class_size=class_size or 30,
            native_language=native_language or "中文",
            teaching_intent=teaching_intent,
        )

        from app.services.rag import RAGGenerator
        from app.core.config import settings

        model_name = getattr(settings, "LLM_MODEL", "deepseek-chat")
        generator = RAGGenerator(
            api_key=getattr(settings, "LLM_API_KEY", None),
            api_base=getattr(settings, "LLM_BASE_URL", None),
            model=model_name,
            max_tokens=6000,
            temperature=0.5,
        )

        if generator.use_api:
            system_prompt, _ = render_prompt(WORD_PROMPT_NAME)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            answer, _usage = generator._generate_with_api(messages)
            raw_answer = answer
            outline = _extract_json_object(answer)
            reason = _validate_word_outline(outline, min_sections)

            if reason:
                retries = 1
                logger.warning(f"Word 结构首次校验失败（{reason}），重试一次")
                messages += [
                    {"role": "assistant", "content": answer[-2000:]},
                    {"role": "user", "content": f"上一次输出未通过结构校验：{reason}。请重新输出完整的文档结构 JSON，严格遵循输出契约。"},
                ]
                answer, _usage = generator._generate_with_api(messages)
                raw_answer = answer
                outline = _extract_json_object(answer)
                reason = _validate_word_outline(outline, min_sections)

            if reason:
                logger.warning(f"Word 结构重试仍失败（{reason}），回退确定性结构")
            else:
                fallback_used = False
                self_check = outline.get("self_check") or {}
        else:
            logger.warning("LLM 不可用，Word 回退确定性结构")
    except Exception as e:
        logger.warning(f"Word 课件 LLM 生成失败，回退确定性结构: {e}")

    if fallback_used:
        outline = _fallback_word_outline(title, plan, language_name, duration_minutes)
        self_check = {"prompt_version": "fallback", "notes": "LLM 结构不可用或未通过校验，已用教案确定性文档渲染（简化版生成）"}

    docx_bytes = _render_docx(outline, title)
    return WordCoursewareResult(
        outline=outline,
        docx_bytes=docx_bytes,
        section_count=len(outline.get("sections", [])),
        self_check=self_check,
        prompt_version=version,
        model=model_name if not fallback_used else "template-fallback",
        fallback=fallback_used,
        retries=retries,
        generation_duration=round(time.time() - start_time, 2),
    )
