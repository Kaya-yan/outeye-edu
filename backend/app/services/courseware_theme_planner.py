"""
课件视觉风格规划（④b）：生成课件前的一次轻量 LLM 调用，产出三选一设计简报。

LLM 不可用或输出不合法时，冷启动按课型关键词默认映射兜底——
规划失败绝不阻塞课件生成入口，前端拿到 source 字段可标注"默认推荐"。
"""

import re
from typing import Any, Dict, Optional

from loguru import logger

from app.services.courseware_llm_generator import _build_metrics_lines
from app.services.courseware_themes import (
    THEMES,
    DEFAULT_THEME_ID,
    cold_start_recommend,
    themes_digest_for_planner,
)
from app.services.prompt_manager import render_prompt

PLANNER_PROMPT_NAME = "courseware_theme_planner_v1"

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _cold_start_brief(course_type: str) -> Dict[str, Any]:
    theme_id = cold_start_recommend(course_type)
    theme = THEMES[theme_id]
    return {
        "course_type": course_type or "",
        "recommended_theme": theme_id,
        "reason": f"按课型「{course_type or '未标注'}」默认映射推荐{theme.name}",
        "design_notes": "保持每页单焦点，视觉强调只给最关键信息。",
        "source": "cold_start",
    }


def plan_theme_brief(
    *,
    title: str,
    text: str,
    analysis: Optional[Dict[str, Any]] = None,
    language_name: str = "英语",
    text_level: str = "",
    student_level: str = "",
    course_type: str = "",
    history_digest: str = "（暂无记录）",
) -> Dict[str, Any]:
    """返回 {course_type, recommended_theme, reason, design_notes, source}；source=llm|cold_start"""
    try:
        from app.services.rag import RAGGenerator
        from app.core.config import settings

        generator = RAGGenerator(
            api_key=getattr(settings, "LLM_API_KEY", None),
            api_base=getattr(settings, "LLM_BASE_URL", None),
            model=getattr(settings, "LLM_MODEL", "deepseek-chat"),
            max_tokens=500,
            temperature=0.2,
        )
        if not generator.use_api:
            return _cold_start_brief(course_type)

        excerpt = text[:1500] + ("…（已截断）" if len(text) > 1500 else "")
        system_prompt, user_prompt = render_prompt(
            PLANNER_PROMPT_NAME,
            title=title or "未命名课文",
            language_name=language_name or "英语",
            text_level=text_level or "未标注",
            student_level=student_level or "未标注",
            course_type=course_type or "综合",
            text_excerpt=excerpt,
            metrics_lines=_build_metrics_lines(analysis or {}),
            history_digest=history_digest or "（暂无记录）",
            themes_digest=themes_digest_for_planner(),
        )
        answer, _usage = generator._generate_with_api(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

        import json

        match = _JSON_RE.search(answer)
        if not match:
            logger.warning(f"风格规划输出无 JSON：{answer[:200]}")
            return _cold_start_brief(course_type)
        data = json.loads(match.group(0))
        theme_id = data.get("recommended_theme")
        if theme_id not in THEMES:
            logger.warning(f"风格规划推荐了未知主题 {theme_id!r}，走冷启动映射")
            return _cold_start_brief(course_type)
        return {
            "course_type": str(data.get("course_type") or course_type or "")[:30],
            "recommended_theme": theme_id,
            "reason": str(data.get("reason") or "")[:200] or "基于课文气质推荐",
            "design_notes": str(data.get("design_notes") or "")[:200],
            "source": "llm",
        }
    except Exception as e:
        logger.warning(f"风格规划调用失败，冷启动兜底: {e}")
        return _cold_start_brief(course_type)


def style_history_digest(events: list) -> str:
    """把教师近期主题选择事件压成一行提示词摘要；空历史返回未标注句"""
    if not events:
        return "（暂无记录）"
    counts: Dict[str, int] = {}
    for e in events:
        theme = getattr(e, "theme", None) or "未知"
        counts[theme] = counts.get(theme, 0) + 1
    parts = [f"{THEMES[t].name if t in THEMES else t}×{n}" for t, n in counts.items()]
    return f"近 {len(events)} 次选用：" + "、".join(parts)
