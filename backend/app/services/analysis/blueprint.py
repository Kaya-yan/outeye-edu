"""
教学蓝图（Teaching Blueprint）

从分析结果 + 生成方案中提取高层教学结构，与详细教案分开展示。
"""

from typing import Dict, Any, List


def build_teaching_blueprint(
    analysis: Dict[str, Any],
    plan: Dict[str, Any],
    wiki_results: List[Dict],
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
        "theory_foundations": theory_foundations,
        "activity_count": len(activities),
    }
