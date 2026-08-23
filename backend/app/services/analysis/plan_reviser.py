"""
教案修订引擎（提示词模板 plan_revision_v1 · 九要素骨架）

教师对生成的教案提出修改意见后，基于反馈做最小化修订：
只改被指出的部分，其余章节逐字保留。修订说明单独提取，
不混入正文章节；LLM 不可用时模板回退并显式标注。
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from loguru import logger
import re
import time

from app.services.prompt_manager import render_prompt, prompt_version
from app.services.analysis.fusion_generator import _esc

PROMPT_NAME = "plan_revision_v1"

_SECTION_NAMES = {
    "difficulty_overview": "课文难度概述",
    "suggestions": "教学建议",
    "activities": "课堂环节设计",
    "differentiation": "差异化教学策略",
    "theory": "理论依据",
}


@dataclass
class RevisedPlan:
    """修订后的教案"""
    difficulty_overview: str
    teaching_suggestions: List[str]
    activity_designs: List[Dict[str, str]]
    differentiation: str
    theoretical_basis: str
    revision_note: str          # 修订说明（模型生成，回退时含降级提示）
    generation_duration: float
    model: str
    self_check: Dict[str, Any] = field(default_factory=dict)
    prompt_version: str = ""
    fallback: bool = False


def build_revision_prompt(
    original_plan: Dict[str, Any],
    revision_instruction: str,
    section_to_revise: Optional[str],
    language: Optional[str],
) -> str:
    """按九要素模板构建修订用户 Prompt"""
    activities = original_plan.get("activity_designs", [])
    minutes = _sum_activity_minutes(activities)
    if minutes is not None:
        duration_line = f"各环节时间总和应为 {minutes} 分钟，修订后保持不变"
    else:
        duration_line = "原教案未标注完整环节时间，修订时保持各环节原时长标注不变"

    language_line = f"；语种：{language}" if language else ""
    section_hint = (
        f"\n（教师指定重点修改：{_SECTION_NAMES[section_to_revise]}部分，其余章节原样保留）"
        if section_to_revise in _SECTION_NAMES
        else ""
    )

    _, user_prompt = render_prompt(
        PROMPT_NAME,
        title=_esc(original_plan.get("title", "未命名课文")),
        student_level=_esc(original_plan.get("student_level", "未知")),
        language_line=language_line,
        duration_line=duration_line,
        original_plan=_esc(_format_original_plan(original_plan)),
        revision_instruction=_esc(revision_instruction or "（无具体意见，请整体复核并做必要修正）"),
        section_hint=section_hint,
    )
    return user_prompt


def _sum_activity_minutes(activities: List[Dict[str, Any]]) -> Optional[int]:
    """求环节时间总和；任一环节缺时间标注则返回 None（不猜）"""
    total = 0
    for act in activities:
        m = re.search(r"(\d+)", str(act.get("duration", "")))
        if not m:
            return None
        total += int(m.group(1))
    return total if total > 0 else None


def _format_original_plan(original_plan: Dict[str, Any]) -> str:
    """把结构化原教案渲染为模板输入的文本形式"""
    parts = [
        "### 一、课文难度概述",
        str(original_plan.get("difficulty_overview", "（无）")),
        "### 二、教学建议",
        _format_suggestions(original_plan.get("teaching_suggestions", [])),
        "### 三、课堂环节设计",
        _format_activities(original_plan.get("activity_designs", [])),
        "### 四、差异化教学策略",
        str(original_plan.get("differentiation", "（无）")),
        "### 五、理论依据",
        str(original_plan.get("theoretical_basis", "（无）")),
    ]
    return "\n".join(parts)


def _format_suggestions(suggestions: list) -> str:
    if not suggestions:
        return "（无）"
    return "\n".join(f"{i+1}. {s}" for i, s in enumerate(suggestions))


def _format_activities(activities: list) -> str:
    if not activities:
        return "（无）"
    parts = []
    for i, act in enumerate(activities, 1):
        name = act.get("name", f"活动{i}")
        header = f"环节{i}：{name}"
        if act.get("duration"):
            header += f"（{act['duration']}）"
        parts.append(header)
        if act.get("objective"):
            parts.append(f"- 目标：{act['objective']}")
        if act.get("steps"):
            parts.append(f"- 步骤：{act['steps']}")
        if act.get("assessment"):
            parts.append(f"- 评估点：{act['assessment']}")
    return "\n".join(parts)


def _extract_revision_note(answer: str) -> tuple:
    """把"修订说明"章节从回答中剥离，避免混入理论依据；返回 (note, 去除后的回答)"""
    m = re.search(
        r"^#{0,3}\s*\**\s*(?:修订说明|修改说明)\s*\**\s*[：:]?\s*\n(.*?)(?=```|\Z)",
        answer,
        re.M | re.S,
    )
    if not m:
        return "", answer
    note = m.group(1).strip()
    cleaned = (answer[:m.start()] + answer[m.end():]).rstrip()
    return note, cleaned


def revise_teaching_plan(
    original_plan: Dict[str, Any],
    revision_instruction: str,
    text: str,
    title: str,
    student_level: str,
    language: Optional[str] = None,
    section_to_revise: Optional[str] = None,
) -> RevisedPlan:
    """
    基于教师反馈修订教案

    Args:
        original_plan: 原始教案（各 section 的 dict）
        revision_instruction: 教师的修改意见
        text: 原始课文（当前不参与修订，保留参数以兼容端点）
        title: 课文标题
        student_level: 学生水平
        language: 语言
        section_to_revise: 要修改的部分（可选）

    Returns:
        修订后的教案
    """
    start_time = time.time()
    version = prompt_version(PROMPT_NAME)

    enriched_plan = dict(original_plan)
    enriched_plan.setdefault("title", title)
    enriched_plan.setdefault("student_level", student_level)

    user_prompt = build_revision_prompt(
        original_plan=enriched_plan,
        revision_instruction=revision_instruction,
        section_to_revise=section_to_revise,
        language=language,
    )

    model_name = "deepseek-chat"
    fallback_used = False
    answer = ""
    try:
        from app.services.rag import RAGGenerator
        from app.core.config import settings

        model_name = getattr(settings, 'LLM_MODEL', 'deepseek-chat')
        generator = RAGGenerator(
            api_key=getattr(settings, 'LLM_API_KEY', None),
            api_base=getattr(settings, 'LLM_BASE_URL', None),
            model=model_name,
            max_tokens=4096,
            temperature=0.5,
        )

        system_prompt, _ = render_prompt(PROMPT_NAME)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        if generator.use_api:
            answer, usage = generator._generate_with_api(messages)
        else:
            fallback_used = True
            answer = _fallback_revise(enriched_plan, revision_instruction)
    except Exception as e:
        logger.warning(f"LLM修订失败，使用模板回退: {e}")
        fallback_used = True
        answer = _fallback_revise(enriched_plan, revision_instruction)

    if fallback_used:
        model_name = "template-fallback"

    note, body = _extract_revision_note(answer)

    from app.services.analysis.fusion_generator import _parse_plan
    plan = _parse_plan(
        body, [], [], time.time() - start_time,
        model_name=model_name,
        prompt_version=version,
        fallback=fallback_used,
    )

    revision_note = note or f"根据教师意见修订：{revision_instruction[:100]}"
    if fallback_used and "不可用" not in revision_note:
        revision_note += "（AI 修订服务暂时不可用，以上为原始教案）"

    return RevisedPlan(
        difficulty_overview=plan.difficulty_overview,
        teaching_suggestions=plan.teaching_suggestions,
        activity_designs=plan.activity_designs,
        differentiation=plan.differentiation,
        theoretical_basis=plan.theoretical_basis,
        revision_note=revision_note,
        generation_duration=round(time.time() - start_time, 2),
        model=model_name,
        self_check=plan.self_check,
        prompt_version=version,
        fallback=fallback_used,
    )


def _fallback_revise(original_plan: Dict[str, Any], instruction: str) -> str:
    """LLM不可用时的回退：保留原教案，附加修订说明"""
    return _format_original_plan(original_plan) + f"""

### 修订说明
教师意见：{instruction}
（注意：AI修订服务暂时不可用，以上为原始教案。请手动根据教师意见修改。）"""
