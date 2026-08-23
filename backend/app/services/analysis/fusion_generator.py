"""
融合生成引擎 - OutEye Edu 1.0 ADDSR-Lite（提示词 v2 · 九要素骨架）

将白盒分析结果 + 双源检索结果 + 教学设置组装为结构化 Prompt
（模板文件 app/prompts/lesson_plan_v2.md），调用 LLM 生成面向教师的完整教案：

一、教学设计框架选择（PWP/PPP/TBLT/过程写作法，CoT 声明依据）
二、教学目标（3-5 条可测量，Bloom 层级 + 评估方式）
三、课文难度概述
四、教学建议（数据依据 + 理论依据）
五、课堂环节设计（4-6 环节，时间总和 = 课时）
六、评估设计（形成性 ≥2 + 终结性 ≥2）
七、差异化教学策略
八、理论依据
+ self_check 自检 JSON（随产物落库，前端校验提示）
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from loguru import logger
import time
import re
import json

from app.services.prompt_manager import render_prompt, prompt_version

PROMPT_NAME = "lesson_plan_v2"

CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


@dataclass
class TeachingPlan:
    """教学方案"""
    framework: str                      # 教学设计框架及选择依据
    objectives: List[Dict[str, str]]    # 教学目标（text/bloom/assessment）
    difficulty_overview: str            # 课文难度概述
    teaching_suggestions: List[str]     # 教学建议
    activity_designs: List[Dict[str, str]]  # 课堂环节设计
    assessment: Dict[str, List[str]]    # 评估设计（formative/summative）
    differentiation: str                # 差异化教学策略
    theoretical_basis: str              # 理论依据
    sources: List[Dict[str, Any]]       # 参考来源
    generation_duration: float
    model: str
    evidence_annotations: Dict[str, Any] = field(default_factory=dict)  # 可追溯证据标注
    self_check: Dict[str, Any] = field(default_factory=dict)  # 模型自检结果
    prompt_version: str = ""
    fallback: bool = False
    raw_response: str = ""  # LLM 原始输出（回归脚本落盘对比用，不进 API 响应）


def _esc(value: str) -> str:
    """转义 string.Template 的 $ 占位符语法，防止课文/检索内容干扰渲染。"""
    return value.replace("$", "$$") if isinstance(value, str) else value


def prepare_text(text: str, hard_limit: int = 12000) -> str:
    """
    课文全文传入；超长课文智能分段摘要：
    开头全文 + 中段逐段首句摘要 + 结尾全文，保证首尾语境完整。
    """
    if not text:
        return ""
    if len(text) <= hard_limit:
        return text

    head = text[:6000]
    tail = text[-2500:]
    middle = text[6000:-2500]
    paras = [p.strip() for p in middle.split("\n") if p.strip()]
    digest_lines = []
    for i, p in enumerate(paras[:40], 1):
        first_sentence = re.split(r"(?<=[.!?。！？])\s+", p)[0][:120]
        digest_lines.append(f"[中段摘要·第{i}段] {first_sentence}")
    digest = "\n".join(digest_lines)
    note = f"（原文共 {len(text)} 字符，超出单次传入上限：开头与结尾保留全文，中段提供逐段首句摘要）"
    return f"{note}\n\n{head}\n\n【—— 中段摘要 ——】\n{digest}\n\n【—— 结尾恢复全文 ——】\n{tail}"


def _build_cefr_line(cefr_distribution: Dict[str, Any]) -> str:
    """白盒产出键名为 A1/A2/.../unknown，按原键直传（修复旧版 A1-A2 键名错位致全 0）。"""
    dist = cefr_distribution or {}
    parts = [f"{lvl}={dist.get(lvl, 0)}" for lvl in CEFR_LEVELS]
    parts.append(f"未分级={dist.get('unknown', 0)}")
    return "，".join(parts)


def build_fusion_prompt(
    text_title: str,
    text_content: str,
    analysis: Dict[str, Any],
    wiki_context: str,
    rag_context: str,
    duration_minutes: int = 90,
    course_type: Optional[str] = None,
    class_size: Optional[int] = None,
    native_language: Optional[str] = None,
) -> str:
    """按九要素模板构建用户 Prompt"""

    vocab = analysis.get("vocabulary", {})
    syntax = analysis.get("syntax", {})
    discourse = analysis.get("discourse", {})
    learner_gap = analysis.get("learner_gap", {})
    tags = analysis.get("enhancement_tags", [])
    insights = analysis.get("teaching_insights", [])
    lang = analysis.get("language", "en")
    lang_name = analysis.get("language_name", "英语")

    lang_notes = {
        "ja": "。注意：日语课文需考虑助词、动词活用、敬语体系",
        "fr": "。注意：法语课文需考虑性数变化、动词变位、代词位置",
        "de": "。注意：德语课文需考虑格变化、框型结构、复合词",
        "es": "。注意：西班牙语课文需考虑动词变位、虚拟式、性数一致",
        "ko": "。注意：韩语课文需考虑助词、敬语、语序",
    }
    language_note = lang_notes.get(lang, "")

    cultural_elements = analysis.get("cultural_elements", [])
    if cultural_elements:
        cultural_lines = [
            f"- [{_esc(str(e.get('category', '')))}] {_esc(str(e.get('keyword', '')))}：{_esc(str(e.get('explanation', '')))}"
            for e in cultural_elements
        ]
        cultural_section = "\n### 文化背景元素（关键词检测）\n" + "\n".join(cultural_lines)
    else:
        cultural_section = ""

    awl_line = (
        f"AWL 学术词汇：{vocab.get('awl_count', 0)} 个（占比 {vocab.get('awl_ratio', 0) * 100:.1f}%）"
        if lang == "en"
        else "AWL 学术词汇：不适用（非英语课文）"
    )

    max_sent = syntax.get("max_sentence", {}) or {}
    difficult = ", ".join(
        d.get("word", "") for d in vocab.get("difficult_words", [])[:8]
    ) or "（无）"
    insight_line = "；".join(str(t) for t in insights[:6]) or "（无）"

    variables = dict(
        title=_esc(text_title or "未命名课文"),
        language_name=_esc(lang_name),
        text_level=analysis.get("text_level", "未知"),
        student_level=learner_gap.get("student_level", "未知"),
        gap_line=_esc(f"{learner_gap.get('gap', '')} — {learner_gap.get('gap_description', '')}"),
        duration_minutes=int(duration_minutes or 90),
        course_type=_esc(course_type or "综合"),
        class_size=int(class_size or 30),
        native_language=_esc(native_language or "中文"),
        language_note=language_note,
        full_text=_esc(prepare_text(text_content or "")),
        total_words=vocab.get("total_words", 0),
        unique_words=vocab.get("unique_words", 0),
        cefr_line=_build_cefr_line(vocab.get("cefr_distribution", {})),
        awl_line=awl_line,
        difficult_words=_esc(difficult),
        avg_sentence_length=syntax.get("avg_sentence_length", 0),
        max_sent_index=(max_sent.get("index", 0) or 0) + 1,
        max_sent_words=max_sent.get("word_count", 0),
        max_sent_preview=_esc(max_sent.get("preview", ""))[:60],
        long_sentences_count=syntax.get("long_sentences_count", 0),
        flesch=syntax.get("flesch_reading_ease", 0),
        paragraph_count=discourse.get("paragraph_count", 0),
        connective_density=discourse.get("connective_density", 0),
        genre_hint=_esc(str(discourse.get("genre_hint", "未知"))),
        cultural_section=cultural_section,
        wiki_context=_esc(wiki_context or "（未检索到相关理论）"),
        rag_context=_esc(rag_context or "（未检索到相关资源）"),
        tags_line=_esc(", ".join(tags)),
        insights_line=_esc(insight_line),
    )

    _, user_prompt = render_prompt(PROMPT_NAME, **variables)
    return user_prompt


def build_wiki_context(wiki_results: List[Dict]) -> str:
    """将 Wiki 结果组装为上下文字符串"""
    if not wiki_results:
        return ""
    parts = []
    for i, r in enumerate(wiki_results, 1):
        title = r.get("title", f"Wiki条目{i}")
        summary = r.get("summary", "")[:300]
        confidence = r.get("confidence", "")
        contested = r.get("contested", False)
        contradictions = r.get("contradictions", []) or []
        sources = r.get("sources", []) or []
        updated = r.get("updated", "")

        meta_parts = []
        if confidence:
            meta_parts.append(f"置信度：{confidence}")
        if updated:
            meta_parts.append(f"更新时间：{updated}")
        meta_parts.append(f"来源：{len(sources)}")

        lines = [f"[Wiki {i}] {title}"]
        if meta_parts:
            lines.append(" | ".join(meta_parts))
        lines.append("争议状态：存在争议" if contested else "争议状态：无显式争议")
        if contradictions:
            lines.append(f"冲突页：{', '.join(contradictions)}")
        if summary:
            lines.append(summary)
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def build_rag_context(rag_results: List[Dict]) -> str:
    """将 RAG 结果组装为上下文字符串"""
    if not rag_results:
        return ""
    parts = []
    for i, r in enumerate(rag_results, 1):
        title = r.get("metadata", {}).get("title", f"文档{i}")
        content = r.get("content", "")[:300]
        parts.append(f"[资源 {i}] {title}\n{content}")
    return "\n\n".join(parts)


def generate_teaching_plan(
    text_title: str,
    text_content: str,
    analysis: Dict[str, Any],
    wiki_results: List[Dict],
    rag_results: List[Dict],
    mode: str = "enhanced",
    duration_minutes: int = 90,
    course_type: Optional[str] = None,
    class_size: Optional[int] = None,
    native_language: Optional[str] = None,
) -> TeachingPlan:
    """
    生成教学方案

    Args:
        text_title: 课文标题
        text_content: 课文内容
        analysis: 白盒分析结果（完整响应）
        wiki_results: Wiki 检索结果
        rag_results: RAG 检索结果
        mode: 生成模式（basic 精简版 / enhanced 含证据标注）
        duration_minutes: 课时时长（分钟）
        course_type: 课程类型（精读/泛读/听说/写作/综合）
        class_size: 班级人数
        native_language: 学生母语
    """
    start_time = time.time()
    version = prompt_version(PROMPT_NAME)

    wiki_context = build_wiki_context(wiki_results)
    rag_context = build_rag_context(rag_results)

    model_name = "deepseek-chat"
    fallback_used = False
    try:
        user_prompt = build_fusion_prompt(
            text_title=text_title,
            text_content=text_content,
            analysis=analysis,
            wiki_context=wiki_context,
            rag_context=rag_context,
            duration_minutes=duration_minutes,
            course_type=course_type,
            class_size=class_size,
            native_language=native_language,
        )

        from app.services.rag import RAGGenerator
        from app.core.config import settings

        model_name = getattr(settings, 'LLM_MODEL', 'deepseek-chat')
        generator = RAGGenerator(
            api_key=getattr(settings, 'LLM_API_KEY', None),
            api_base=getattr(settings, 'LLM_BASE_URL', None),
            model=model_name,
            max_tokens=4096,
            temperature=0.7,
        )

        system_prompt, _ = render_prompt(PROMPT_NAME)  # 首次调用渲染空变量仅取 system
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        if generator.use_api:
            answer, usage = generator._generate_with_api(messages)
        else:
            fallback_used = True
            answer = _fallback_generate(analysis, duration_minutes)
            usage = {}

    except Exception as e:
        # 模板缺失/渲染失败/LLM 异常统一降级为模板回退（前端显式标注），不 500
        logger.warning(f"教案生成链路异常，使用模板回退: {type(e).__name__}: {e}")
        fallback_used = True
        answer = _fallback_generate(analysis, duration_minutes)
        usage = {}

    if fallback_used:
        model_name = "template-fallback"

    plan = _parse_plan(
        answer, wiki_results, rag_results,
        time.time() - start_time,
        model_name=model_name,
        prompt_version=version,
        fallback=fallback_used,
    )

    # 可追溯证据标注：仅增强模式为每条建议/环节绑定引用或显式降级
    if mode == "enhanced":
        from app.services.analysis.citation import annotate_plan
        plan_dict = {
            "difficulty_overview": plan.difficulty_overview,
            "teaching_suggestions": plan.teaching_suggestions,
            "activity_designs": plan.activity_designs,
            "differentiation": plan.differentiation,
            "theoretical_basis": plan.theoretical_basis,
        }
        plan.evidence_annotations = annotate_plan(plan_dict, wiki_results, rag_results)
    else:
        plan.evidence_annotations = {}

    return plan


# ============ 解析 ============

def _strip_md(line: str) -> str:
    """去掉行首列表符与 ** 加粗标记（LLM 常输出 **目标1**： 这类 Markdown 变体）"""
    s = line.strip()
    s = re.sub(r"^[-*•>]+\s+", "", s)
    s = s.replace("**", "")
    return s.strip()


_SEP_RE = re.compile(r"^[-—–_=~*]{2,}$")

# 章节关键词必须紧跟编号出现，且标题行后缀不含句读：
# 防止"3. 布置课后作业（见评估设计）。"这类句中引用被误判为新章节
_HEADER = r"^\s*[*#\s]{0,8}[一二三四五六七八九十\d]+\s*[、.．:：]\s*"

_SECTION_PATTERNS = [
    ("framework", re.compile(_HEADER + r"(?:教学设计)?框架选择[^。；;，,]{0,25}$")),
    ("objectives", re.compile(_HEADER + r"教学目标[^。；;，,]{0,25}$")),
    ("difficulty_overview", re.compile(_HEADER + r"(?:课文)?难度概述[^。；;，,]{0,25}$")),
    ("teaching_suggestions", re.compile(_HEADER + r"教学建议[^。；;，,]{0,25}$")),
    ("activity_designs", re.compile(_HEADER + r"(?:课堂)?(?:环节|活动)设计[^。；;，,]{0,25}$")),
    ("assessment", re.compile(_HEADER + r"评估设计[^。；;，,]{0,25}$")),
    ("differentiation", re.compile(_HEADER + r"差异化(?:教学)?策略[^。；;，,]{0,25}$")),
    ("theoretical_basis", re.compile(_HEADER + r"理论依据[^。；;，,]{0,25}$")),
]


def _parse_plan(
    answer: str,
    wiki_results: List[Dict],
    rag_results: List[Dict],
    duration: float,
    model_name: str = "deepseek-chat",
    prompt_version: str = "",
    fallback: bool = False,
) -> TeachingPlan:
    """解析 LLM 输出为结构化教学方案"""
    prompt_version_kw = prompt_version  # 避免与导入的函数同名
    sections = {
        "framework": "",
        "objectives_raw": [],
        "difficulty_overview": "",
        "teaching_suggestions": [],
        "activity_designs": [],
        "assessment_raw": [],
        "differentiation": "",
        "theoretical_basis": "",
    }

    current_section = None
    current_content: List[str] = []

    def _flush_section():
        nonlocal current_section, current_content
        if current_section == "framework":
            if not sections["framework"]:
                sections["framework"] = "\n".join(current_content).strip()
        elif current_section == "objectives":
            sections["objectives_raw"].extend(current_content)
        elif current_section == "difficulty_overview":
            if not sections["difficulty_overview"]:
                sections["difficulty_overview"] = "\n".join(current_content).strip()
        elif current_section == "teaching_suggestions":
            sections["teaching_suggestions"].extend(_extract_list_items(current_content))
        elif current_section == "activity_designs":
            sections["activity_designs"].extend(_extract_activities(current_content))
        elif current_section == "assessment":
            sections["assessment_raw"].extend(current_content)
        elif current_section == "differentiation":
            if not sections["differentiation"]:
                sections["differentiation"] = "\n".join(current_content).strip()
        elif current_section == "theoretical_basis":
            if not sections["theoretical_basis"]:
                sections["theoretical_basis"] = "\n".join(current_content).strip()

    self_check = _extract_self_check(answer)

    in_fence = False
    for line in answer.split("\n"):
        line_stripped = line.strip()
        # 跳过 ``` 代码块（self_check JSON 由 _extract_self_check 单独提取，
        # 不能混入最后一个章节的正文）
        if line_stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line_stripped or _SEP_RE.match(line_stripped):
            continue
        matched = False
        for section_name, pattern in _SECTION_PATTERNS:
            if pattern.search(line_stripped):
                _flush_section()
                current_section = section_name
                current_content = []
                matched = True
                break
        if not matched:
            current_content.append(_strip_md(line_stripped))

    _flush_section()

    # 兜底：完全没解析出章节时，整段回答放进概述
    if not sections["difficulty_overview"] and not sections["teaching_suggestions"]:
        sections["difficulty_overview"] = answer[:500]

    objectives = _parse_objectives(sections["objectives_raw"])
    assessment = _parse_assessment(sections["assessment_raw"])

    if fallback and not self_check:
        self_check = {
            "prompt_version": "fallback",
            "notes": "LLM 不可用，模板降级生成，目标与评估为占位内容，需人工核对",
        }

    sources = []
    for r in wiki_results[:3]:
        sources.append({"type": "wiki", "title": r.get("title", ""), "score": r.get("relevance_score", 0)})
    for r in rag_results[:3]:
        sources.append({"type": "rag", "title": r.get("metadata", {}).get("title", ""), "score": r.get("score", 0)})

    return TeachingPlan(
        framework=sections["framework"],
        objectives=objectives,
        difficulty_overview=sections["difficulty_overview"],
        teaching_suggestions=sections["teaching_suggestions"],
        activity_designs=sections["activity_designs"],
        assessment=assessment,
        differentiation=sections["differentiation"],
        theoretical_basis=sections["theoretical_basis"],
        sources=sources,
        generation_duration=round(duration, 2),
        model=model_name,
        self_check=self_check,
        prompt_version=prompt_version_kw,
        fallback=fallback,
        raw_response=answer,
    )


def _extract_self_check(answer: str) -> Dict[str, Any]:
    """提取输出末尾的 ```json 自检块"""
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", answer, re.DOTALL)
    for block in reversed(blocks):
        try:
            data = json.loads(block)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return {}


def _parse_objectives(lines: List[str]) -> List[Dict[str, str]]:
    """解析目标块（行已去 Markdown）：目标N：xxx（Bloom：X）/ 评估方式：yyy"""
    objectives: List[Dict[str, str]] = []
    header_re = re.compile(r"^目标\s*\d*\s*[：:]\s*(.+)$")
    bloom_re = re.compile(r"[（(]\s*Bloom\s*[：:]\s*([^）)]+?)\s*[）)]", re.IGNORECASE)
    assess_re = re.compile(r"^评估方式\s*[：:]\s*(.+)$")

    current: Optional[Dict[str, str]] = None
    for line in lines:
        if _SEP_RE.match(line):
            continue
        header_match = header_re.match(line)
        assess_match = assess_re.match(line)
        if header_match:
            if current:
                objectives.append(current)
            text = header_match.group(1).strip()
            bloom_match = bloom_re.search(text)
            bloom = bloom_match.group(1).strip() if bloom_match else ""
            if bloom_match:
                text = text[:bloom_match.start()].strip().rstrip("，,、")
            current = {"text": text, "bloom": bloom, "assessment": ""}
        elif assess_match and current:
            current["assessment"] = assess_match.group(1).strip()
        elif current and not current["assessment"]:
            # 无显式"评估方式"标签时，取紧跟的一行作为评估说明
            current["assessment"] = line.strip()
    if current:
        objectives.append(current)
    return objectives


def _parse_assessment(lines: List[str]) -> Dict[str, List[str]]:
    """解析评估块（行已去 Markdown）：形成性/终结性两组"""
    result: Dict[str, List[str]] = {"formative": [], "summative": []}
    bucket = "formative"
    marker_re = re.compile(r"^\d+\s*[.、)]\s*")

    def _add(bucket_key: str, rest: str):
        rest = rest.strip()
        if not rest:
            return
        parts = [p.strip() for p in re.split(r"[；;]", rest) if p.strip()]
        result[bucket_key].extend(parts)

    for line in lines:
        if _SEP_RE.match(line):
            continue
        m_form = re.match(r"^形成性评估点?\s*\d*\s*[：:]?\s*(.*)$", line)
        m_summ = re.match(r"^终结性评估点?\s*\d*\s*[：:]?\s*(.*)$", line)
        if m_form:
            bucket = "formative"
            _add("formative", m_form.group(1))
            continue
        if m_summ:
            bucket = "summative"
            _add("summative", m_summ.group(1))
            continue
        numbered = bool(marker_re.match(line))
        cleaned = marker_re.sub("", line.strip())
        if not cleaned:
            continue
        if numbered or not result[bucket]:
            result[bucket].append(cleaned)
        else:
            # 无编号的续行并入上一条，保持子项与父项的关联
            result[bucket][-1] += " " + cleaned
    return result


def _extract_list_items(lines: List[str]) -> List[str]:
    """提取列表项（行已去 Markdown）：编号/圆点项 + "建议N："式条目头，子行并入所属条目"""
    marker_re = re.compile(r"^(?:\d+\s*[.、)]\s*|[-*•]\s+)")
    head_re = re.compile(r"^(?:建议|要点|策略|措施|方法)\s*\d*\s*[：:]")
    items = []
    current = []
    for line in lines:
        if _SEP_RE.match(line):
            continue
        if marker_re.match(line) or head_re.match(line):
            if current:
                items.append(" ".join(current))
            current = [marker_re.sub("", line)]
        else:
            current.append(line)
    if current:
        items.append(" ".join(current))
    return items


def _extract_activities(lines: List[str]) -> List[Dict[str, str]]:
    """提取环节设计（行已去 Markdown）：环节N：名称（X 分钟）+ 目标/步骤/评估点字段，
    步骤为多行编号子列表时逐行累积。"""
    activities = []
    current: Dict[str, str] = {}
    header_re = re.compile(r"^(?:环节|活动)\s*\d*\s*[：:]\s*(.+?)\s*(?:[（(]\s*(\d+)\s*分钟\s*[）)])?\s*$")
    field_re = re.compile(r"^(目标|步骤|时间|时长|评估点)\s*[：:]\s*(.*)$")
    skip_re = re.compile(r"^(?:时间合计|合计|总计)")
    last_field = None

    for line in lines:
        if _SEP_RE.match(line) or skip_re.match(line):
            continue
        header_match = header_re.match(line)
        field_match = field_re.match(line)

        if header_match:
            if current:
                activities.append(current)
            current = {
                "name": header_match.group(1).strip(),
                "duration": f"{header_match.group(2)}分钟" if header_match.group(2) else "",
            }
            last_field = None
        elif field_match:
            key_map = {"目标": "objective", "步骤": "steps", "时间": "duration", "时长": "duration", "评估点": "assessment"}
            field_name = key_map.get(field_match.group(1), field_match.group(1))
            value = field_match.group(2).strip()
            current[field_name] = value
            last_field = field_name
        elif current and last_field:
            current[last_field] = (current[last_field] + "\n" + line).strip()

    if current:
        activities.append(current)
    return activities


def _fallback_generate(
    analysis: Dict[str, Any],
    duration_minutes: int = 90,
) -> str:
    """LLM 不可用时的模板回退（降级生成，前端会明确标注）"""
    tips = analysis.get("teaching_tips") or analysis.get("teaching_insights", [])
    gap = analysis.get("learner_gap", {})
    lang = analysis.get("language", "en")
    lang_name = analysis.get("language_name", "英语")

    if lang == "ja":
        activity_note = "（注：日语课文应重点关注助词、动词活用、敬语等语法特征）"
    elif lang == "ko":
        activity_note = "（注：韩语课文应重点关注助词、敬语、语序等语法特征）"
    elif lang in ("fr", "de", "es"):
        activity_note = f"（注：{lang_name}课文应关注动词变位、性数变化等语法特征）"
    else:
        activity_note = ""

    total = int(duration_minutes or 90)
    splits = {"导入": 0.12, "呈现": 0.28, "操练": 0.32, "产出": 0.18, "总结": 0.10}
    minutes = {}
    allocated = 0
    names = list(splits.keys())
    for i, name in enumerate(names):
        if i == len(names) - 1:
            minutes[name] = total - allocated
        else:
            m = round(total * splits[name])
            minutes[name] = m
            allocated += m

    plan = f"""### 一、教学设计框架选择
PWP（读前-读中-读后）。依据：体裁提示为{analysis.get('genre_hint', analysis.get('discourse', {}).get('genre_hint', '阅读材料'))}，默认按阅读课组织。（模板降级默认，请人工确认）

### 二、教学目标
目标1：能认读并说出本课 5 个超纲词的常用释义（Bloom：记忆）
- 评估方式：词卡快问快答，答对 4/5 为达标
目标2：能概括各段落大意并复述课文主线（Bloom：理解）
- 评估方式：读后口头复述，覆盖主线要点 3 个以上
目标3：能仿写课文中出现的关键句型各 1 句（Bloom：应用）
- 评估方式：书面仿写，句型结构与用法正确

### 三、课文难度概述
课文等级为{analysis.get('text_level', '未知')}，学生水平为{gap.get('student_level', '未知')}。
差距判断：{gap.get('gap', '')} — {gap.get('gap_description', '')}。
语种：{lang_name}{activity_note}

### 四、教学建议
"""
    for i, tip in enumerate(tips, 1):
        plan += f"{i}. {tip}\n"
    if not tips:
        plan += "1. 建议先解决超纲词，再进入段落大意理解，最后做句型仿写输出。\n"

    plan += f"""
### 五、课堂环节设计
环节1：导入激趣（{minutes['导入']} 分钟）
- 目标：激活话题背景知识
- 步骤：图片/问题导入，学生猜测课文主题，快速浏览标题与首段验证
- 评估点：口头回答是否触及主题关键词

环节2：呈现与词汇预处理（{minutes['呈现']} 分钟）
- 目标：指向目标 1
- 步骤：呈现超纲词与例句，图文匹配，全班跟读后两两互测
- 评估点：词卡快问快答正确率

环节3：操练-读中理解（{minutes['操练']} 分钟）
- 目标：指向目标 2
- 步骤：逐段阅读并归纳段落大意，小组核对，教师带领拆解最长句结构
- 评估点：段落大意卡匹配情况

环节4：产出-句型仿写（{minutes['产出']} 分钟）
- 目标：指向目标 3
- 步骤：从课文中提炼关键句型，学生仿写并同伴互评
- 评估点：仿写句子结构与用法

环节5：总结与作业（{minutes['总结']} 分钟）
- 目标：收束课堂、布置分层作业
- 步骤：思维导图总结课文主线，布置基础/进阶/挑战三层作业
- 评估点：口头总结完整性

### 六、评估设计
- 形成性评估点：环节 2 词卡快问快答；环节 3 段落大意匹配；环节 4 仿写互评
- 终结性评估点：课后完成 5 句关键句型仿写（按结构正确性评分）；下节课听写超纲词（5 词，4 词正确为达标）

### 七、差异化教学策略
- **基础层**：提供双语词汇表和段落大意预览，只做主旨理解任务
- **进阶层**：标准阅读+词汇练习+语篇分析
- **挑战层**：深度分析+批判性思维+创意写作

### 八、理论依据
本方案基于Krashen的输入假说（i+1原则）和Vygotsky的最近发展区理论（ZPD），
通过提供适当的支架帮助学生理解略高于当前水平的文本。

```json
{{"prompt_version": "fallback", "framework": "PWP（模板默认）", "objectives_count": 3, "objectives_measurable": true, "stage_count": 5, "time_sum_minutes": {total}, "time_matches_duration": true, "formative_checks": 3, "summative_checks": 2, "no_copy_paste": true, "notes": "LLM 不可用，模板降级生成，请人工核对目标与环节是否适配本课文"}}
```"""
    return plan
