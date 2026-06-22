"""
教案修订引擎

教师对生成的教案提出修改意见后，基于反馈重新生成被修改的部分。
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from loguru import logger
import time


@dataclass
class RevisedPlan:
    """修订后的教案"""
    difficulty_overview: str
    teaching_suggestions: List[str]
    activity_designs: List[Dict[str, str]]
    differentiation: str
    theoretical_basis: str
    revision_note: str          # 修订说明
    generation_duration: float
    model: str


REVISION_SYSTEM_PROMPT = """你是一位资深外语教学专家。教师对之前生成的教学方案提出了修改意见。

你的任务是根据教师的修改意见修订教案。修订原则：
1. 只修改被指出的问题，保留其余内容
2. 如果教师的意见与教学理论冲突，请解释原因并提供折中方案
3. 保持输出格式与原教案一致
4. 使用中文输出"""


def build_revision_prompt(
    original_plan: Dict[str, Any],
    revision_instruction: str,
    section_to_revise: Optional[str],
    analysis_summary: str,
) -> str:
    """构建修订 Prompt"""

    section_names = {
        "difficulty_overview": "课文难度概述",
        "suggestions": "教学建议",
        "activities": "课堂活动设计",
        "differentiation": "差异化教学策略",
        "theory": "理论依据",
    }

    section_hint = ""
    if section_to_revise and section_to_revise in section_names:
        section_hint = f"\n重点修改：{section_names[section_to_revise]}部分"

    prompt = f"""## 原始教案

### 一、课文难度概述
{original_plan.get('difficulty_overview', '（无）')}

### 二、教学建议
{_format_suggestions(original_plan.get('teaching_suggestions', []))}

### 三、课堂活动设计
{_format_activities(original_plan.get('activity_designs', []))}

### 四、差异化教学策略
{original_plan.get('differentiation', '（无）')}

### 五、理论依据
{original_plan.get('theoretical_basis', '（无）')}

## 课文分析摘要
{analysis_summary}

## 教师修改意见
{revision_instruction}{section_hint}

## 请输出修订后的教案

按以下格式输出：

### 一、课文难度概述
（修订后的内容）

### 二、教学建议
（修订后的内容）

### 三、课堂活动设计
（修订后的内容）

### 四、差异化教学策略
（修订后的内容）

### 五、理论依据
（修订后的内容）

### 修订说明
（简要说明修改了哪些内容、为什么这样修改）"""

    return prompt


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
        parts.append(f"活动：{name}")
        if act.get("objective"):
            parts.append(f"  目标：{act['objective']}")
        if act.get("steps"):
            parts.append(f"  步骤：{act['steps']}")
        if act.get("duration"):
            parts.append(f"  时间：{act['duration']}")
    return "\n".join(parts)


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
        original_plan: 原始教案（4个section的dict）
        revision_instruction: 教师的修改意见
        text: 原始课文
        title: 课文标题
        student_level: 学生水平
        language: 语言
        section_to_revise: 要修改的部分（可选）

    Returns:
        修订后的教案
    """
    start_time = time.time()

    # 构建分析摘要
    analysis_summary = f"课文：{title}\n学生水平：{student_level}"
    if language:
        analysis_summary += f"\n语种：{language}"

    # 构建 Prompt
    user_prompt = build_revision_prompt(
        original_plan=original_plan,
        revision_instruction=revision_instruction,
        section_to_revise=section_to_revise,
        analysis_summary=analysis_summary,
    )

    # 调用 LLM
    model_name = "deepseek-chat"
    try:
        from app.services.rag import RAGGenerator
        from app.core.config import settings

        model_name = getattr(settings, 'LLM_MODEL', 'deepseek-chat')
        generator = RAGGenerator(
            api_key=getattr(settings, 'LLM_API_KEY', None),
            api_base=getattr(settings, 'LLM_BASE_URL', None),
            model=model_name,
            max_tokens=2048,
            temperature=0.7,
        )

        messages = [
            {"role": "system", "content": REVISION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        if generator.use_api:
            answer, usage = generator._generate_with_api(messages)
        else:
            answer = _fallback_revise(original_plan, revision_instruction)
    except Exception as e:
        logger.warning(f"LLM修订失败，使用模板回退: {e}")
        answer = _fallback_revise(original_plan, revision_instruction)

    # 解析修订结果
    from app.services.analysis.fusion_generator import _parse_plan
    plan = _parse_plan(answer, [], [], time.time() - start_time, model_name=model_name)

    return RevisedPlan(
        difficulty_overview=plan.difficulty_overview,
        teaching_suggestions=plan.teaching_suggestions,
        activity_designs=plan.activity_designs,
        differentiation=plan.differentiation,
        theoretical_basis=plan.theoretical_basis,
        revision_note=f"根据教师意见修订：{revision_instruction[:100]}",
        generation_duration=round(time.time() - start_time, 2),
        model=model_name,
    )


def _fallback_revise(original_plan: Dict[str, Any], instruction: str) -> str:
    """LLM不可用时的回退：保留原教案，附加修订说明"""
    overview = original_plan.get("difficulty_overview", "")
    suggestions = _format_suggestions(original_plan.get("teaching_suggestions", []))
    activities = _format_activities(original_plan.get("activity_designs", []))
    differentiation = original_plan.get("differentiation", "")
    theory = original_plan.get("theoretical_basis", "")

    return f"""### 一、课文难度概述
{overview}

### 二、教学建议
{suggestions}

### 三、课堂活动设计
{activities}

### 四、差异化教学策略
{differentiation}

### 五、理论依据
{theory}

### 修订说明
教师意见：{instruction}
（注意：AI修订服务暂时不可用，以上为原始教案。请手动根据教师意见修改。）"""
