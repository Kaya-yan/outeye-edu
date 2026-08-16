"""
主动 A/B 两版生成

教师主动生成 baseline（基础版）与 enhanced（增强版）两版，透明比较。
"""

from typing import Dict, Any, List


def build_ab_versions(
    plan: Dict[str, Any],
    analysis: Dict[str, Any],
    wiki_results: List[Dict],
    rag_results: List[Dict],
) -> Dict[str, Any]:
    """构建 baseline 与 enhanced 两版

    - baseline：原始方案（无证据标注、无蓝图）
    - enhanced：带证据引用与教学蓝图（可追溯）
    """
    from app.services.analysis.citation import annotate_plan
    from app.services.analysis.blueprint import build_teaching_blueprint

    # baseline 为原始方案
    baseline = dict(plan)

    # enhanced：在原始方案基础上加证据标注与蓝图
    annotated = annotate_plan(dict(plan), wiki_results, rag_results)
    blueprint = build_teaching_blueprint(analysis, plan, wiki_results)

    enhanced = dict(plan)
    enhanced["evidence_annotations"] = annotated
    enhanced["blueprint"] = blueprint

    return {
        "baseline": baseline,
        "enhanced": enhanced,
    }
