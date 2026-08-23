"""
课件 LLM 生成引擎（FIX-3 · F3.1/F3.2，提示词 courseware_html_v1 · 九要素）

HTML 链路：输入 = 确认版教案 + 白盒指标 + 课文全文 + 教学设置 + 官方组件库，
LLM 生成单文件交互 HTML，落 CoursewareVersion.rendered_html。
解析/校验失败自动重试一次；仍失败回退模板拼装（courseware_bootstrap），
fallback=True 由前端标注"简化版生成"，绝不静默。
PPT / Word 链路（F3.3/F3.4）后续在此模块追加。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4
from loguru import logger
import re
import time

from app.services.prompt_manager import render_prompt, prompt_version
from app.services.analysis.fusion_generator import _esc, prepare_text

PROMPT_NAME = "courseware_html_v1"

_EXTERNAL_RE = re.compile(r"(?:src|href)\s*=\s*[\"']https?://|@import|<link[^>]+stylesheet", re.IGNORECASE)


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


def _extract_html(answer: str) -> str:
    """提取 ```html 代码块；无围栏时退而求完整 <!DOCTYPE …</html> 片段"""
    blocks = re.findall(r"```html\s*(.*?)\s*```", answer, re.DOTALL | re.IGNORECASE)
    if blocks:
        return max(blocks, key=len).strip()
    m = re.search(r"<!DOCTYPE.*?</html>", answer, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(0).strip()
    return ""


def _validate_html(html: str, min_pages: int) -> Optional[str]:
    """返回 None 表示通过，否则返回失败原因（用于重试反馈与回退判定）"""
    if not html:
        return "未找到 HTML 文档（需要 ```html 完整代码块）"
    if "</html>" not in html or "<body" not in html.lower():
        return "HTML 文档不完整（缺少 body 或 </html>）"
    if len(html) < 1500:
        return f"HTML 过短（{len(html)} 字符），疑似截断"
    page_count = len(re.findall(r"data-page\s*=", html))
    if page_count < min_pages:
        return f"页面数不足：需 ≥{min_pages} 个 data-page 页面，实际 {page_count}"
    if not re.search(r"data-component\s*=", html):
        return "缺少 data-component 组件标注"
    if _EXTERNAL_RE.search(html):
        return "存在外链资源（src/href 指向 http、@import 或外链样式表），违反单文件约束"
    return None


def _build_prompt(
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
    components: List[Dict[str, Any]],
) -> str:
    stages = plan.get("activity_designs") or []
    _, user_prompt = render_prompt(
        PROMPT_NAME,
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
        components_digest=_esc(_build_components_digest(components)),
    )
    return user_prompt


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
) -> HTMLCoursewareResult:
    """
    生成单文件交互 HTML 课件。

    LLM 输出经结构校验；失败自动重试一次（携带失败原因）；
    仍失败回退 courseware_bootstrap 模板拼装，fallback=True。
    """
    start_time = time.time()
    version = prompt_version(PROMPT_NAME)
    components = components or []
    min_pages = max(3, len(plan.get("activity_designs") or []) + 1)

    user_prompt = _build_prompt(
        title=title,
        plan=plan,
        analysis=analysis or {},
        text=text,
        language_name=language_name,
        text_level=text_level,
        student_level=student_level,
        duration_minutes=duration_minutes,
        course_type=course_type,
        class_size=class_size,
        native_language=native_language,
        components=components,
    )

    model_name = "template-fallback"
    fallback_used = True
    retries = 0
    html = ""
    self_check: Dict[str, Any] = {}
    raw_answer = ""

    try:
        from app.services.rag import RAGGenerator
        from app.core.config import settings

        model_name = getattr(settings, "LLM_MODEL", "deepseek-chat")
        generator = RAGGenerator(
            api_key=getattr(settings, "LLM_API_KEY", None),
            api_base=getattr(settings, "LLM_BASE_URL", None),
            model=model_name,
            max_tokens=8000,
            temperature=0.7,
        )

        if generator.use_api:
            system_prompt, _ = render_prompt(PROMPT_NAME)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            answer, _usage = generator._generate_with_api(messages)
            raw_answer = answer
            html = _extract_html(answer)
            reason = _validate_html(html, min_pages)

            if reason:
                # F3.5：解析/校验失败自动重试一次，携带失败原因
                retries = 1
                logger.warning(f"HTML 课件首次校验失败（{reason}），重试一次")
                messages += [
                    {"role": "assistant", "content": answer[-2000:]},
                    {"role": "user", "content": f"上一次输出未通过结构校验：{reason}。请重新输出完整的 HTML 文档与自检 JSON，严格遵循输出契约。"},
                ]
                answer, _usage = generator._generate_with_api(messages)
                raw_answer = answer
                html = _extract_html(answer)
                reason = _validate_html(html, min_pages)

            if reason:
                logger.warning(f"HTML 课件重试仍失败（{reason}），回退模板拼装")
            else:
                fallback_used = False
                self_check = _extract_selfcheck(raw_answer)
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
        source_meta = {"generated_by": "llm_html", "prompt_version": version}
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


def _extract_selfcheck(answer: str) -> Dict[str, Any]:
    from app.services.analysis.fusion_generator import _extract_self_check

    return _extract_self_check(answer)
