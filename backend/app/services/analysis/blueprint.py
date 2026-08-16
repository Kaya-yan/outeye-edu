"""
教学蓝图（Teaching Blueprint）

从分析结果 + 生成方案中提取高层教学结构，与详细教案分开展示。
"""

from typing import Dict, Any, List, Optional

# 标准五阶段教学框架
STAGES = ["导入", "讲授", "活动", "检测", "总结"]


def _assign_stages(activities: List[Dict]) -> List[Dict[str, Any]]:
    """将活动按序归入五阶段，缺阶段留空不显示"""
    n = len(activities)
    if n == 0:
        return []

    base = n // len(STAGES)
    extra = n % len(STAGES)

    result = []
    idx = 0
    for i, stage in enumerate(STAGES):
        count = base + (1 if i < extra else 0)
        names = []
        for _ in range(count):
            if idx < n:
                act = activities[idx]
                names.append(act.get("name", f"活动{idx + 1}"))
                idx += 1
        if names:
            result.append({"stage": stage, "activities": names})
    return result


def _build_time_budget(activities: List[Dict], duration_minutes: int) -> Dict[str, Any]:
    """按活动数均分总时长"""
    n = len(activities)
    if n == 0:
        return {"total_minutes": duration_minutes, "activities": []}

    per = duration_minutes // n
    remainder = duration_minutes % n
    items = []
    for i, act in enumerate(activities):
        minutes = per + (1 if i < remainder else 0)
        items.append({
            "name": act.get("name", f"活动{i + 1}"),
            "minutes": minutes,
        })
    return {"total_minutes": duration_minutes, "activities": items}


def _build_evaluation_points(objectives: List[Dict], learner_gap: Dict) -> List[str]:
    """从学习目标与差距派生评价点"""
    points = [obj["objective"] for obj in objectives if obj.get("objective")]
    gap = learner_gap.get("gap")
    if gap:
        points.append(f"差距监控：{gap} - {learner_gap.get('gap_description', '')}")
    return points


def build_teaching_blueprint(
    analysis: Dict[str, Any],
    plan: Dict[str, Any],
    wiki_results: List[Dict],
    rag_results: Optional[List[Dict]] = None,
    duration_minutes: int = 90,
) -> Dict[str, Any]:
    """构建教学蓝图（高层结构，供前端单独展示）"""
    learner_gap = analysis.get("learner_gap", {}) or {}

    # 学习目标：来自活动设计
    activities = plan.get("activity_designs", []) or []
    objectives = []
    for activity in activities:
        if isinstance(activity, dict) and activity.get("objective"):
            objectives.append({
                "activity": activity.get("name", ""),
                "objective": activity["objective"],
            })

    # 理论依据：来自 Wiki 检索，按相关性排序
    theory_foundations = []
    for r in wiki_results or []:
        title = r.get("title", "")
        if title:
            theory_foundations.append({
                "title": title,
                "relevance": r.get("relevance_score", 0),
            })
    theory_foundations.sort(key=lambda x: x["relevance"], reverse=True)

    return {
        "title": analysis.get("text_title", ""),
        "text_level": analysis.get("text_level", ""),
        "student_level": learner_gap.get("student_level", ""),
        "gap": learner_gap.get("gap", ""),
        "gap_description": learner_gap.get("gap_description", ""),
        "objectives": objectives,
        "stages": _assign_stages(activities),
        "time_budget": _build_time_budget(activities, duration_minutes),
        "evaluation_points": _build_evaluation_points(objectives, learner_gap),
        "evidence_types": {
            "theory": len(wiki_results or []),
            "resource": len(rag_results or []),
        },
        "theory_foundations": theory_foundations,
        "activity_count": len(activities),
    }
