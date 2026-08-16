"""
主动 A/B 两版生成测试（TDD）

目标：
1. 教师主动生成 baseline（基础版）与 enhanced（增强版）两版
2. enhanced 版包含证据引用与蓝图，baseline 版为原始输出
3. 两版可透明比较
"""

import pytest

from app.services.analysis.ab_generator import build_ab_versions


class TestBuildABVersions:
    """A/B 两版构建测试"""

    def test_builds_two_versions(self):
        plan = {
            "difficulty_overview": "难度概述",
            "teaching_suggestions": ["基于输入假说的建议"],
            "activity_designs": [{"name": "词汇预习活动", "objective": "掌握新词"}],
        }
        analysis = {"learner_gap": {"student_level": "B1"}}
        wiki_results = [{"title": "输入假说", "relevance_score": 0.9}]
        rag_results = [{"content": "词汇预习活动设计", "metadata": {"title": "词汇资源"}, "score": 0.8}]

        result = build_ab_versions(plan, analysis, wiki_results, rag_results)

        assert "baseline" in result
        assert "enhanced" in result

        # baseline 无证据标注
        assert "evidence_annotations" not in result["baseline"]

        # enhanced 含证据标注与蓝图
        assert "evidence_annotations" in result["enhanced"]
        assert "blueprint" in result["enhanced"]

    def test_enhanced_marks_evidence_on_activity(self):
        plan = {
            "difficulty_overview": "概述",
            "teaching_suggestions": ["基于输入假说的建议"],
            "activity_designs": [{"name": "词汇预习活动", "objective": "掌握新词"}],
        }
        analysis = {"learner_gap": {"student_level": "B1"}}
        wiki_results = [{"title": "输入假说", "relevance_score": 0.9}]
        rag_results = [{"content": "词汇预习活动设计", "metadata": {"title": "词汇资源"}, "score": 0.8}]

        result = build_ab_versions(plan, analysis, wiki_results, rag_results)

        # enhanced 的活动应带 evidence 字段
        annotations = result["enhanced"]["evidence_annotations"]
        activities = annotations.get("activity_designs", [])
        assert len(activities) == 1
        assert "evidence" in activities[0]
