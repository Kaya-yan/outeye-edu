"""
教学蓝图（Teaching Blueprint）测试（TDD）

目标：从分析结果 + 生成方案中提取结构化教学蓝图，与详细教案分开展示。
"""

import pytest

from app.services.analysis.blueprint import build_teaching_blueprint


class TestBuildTeachingBlueprint:
    """教学蓝图构建测试"""

    def test_blueprint_contains_objectives_and_theory(self):
        analysis = {
            "learner_gap": {"student_level": "B1", "gap": "i+1", "gap_description": "略高于当前水平"},
            "text_level": "B2",
        }
        plan = {
            "difficulty_overview": "课文难度中等",
            "theoretical_basis": "基于输入假说",
            "activity_designs": [
                {"name": "词汇预习", "objective": "掌握新词"},
                {"name": "长句拆分", "objective": "理解从句"},
            ],
        }
        wiki_results = [
            {"title": "输入假说", "relevance_score": 0.9},
            {"title": "认知负荷理论", "relevance_score": 0.7},
        ]

        blueprint = build_teaching_blueprint(analysis, plan, wiki_results)

        assert blueprint["student_level"] == "B1"
        assert blueprint["gap"] == "i+1"
        assert len(blueprint["objectives"]) == 2
        assert len(blueprint["theory_foundations"]) == 2
        # 理论按相关性排序
        assert blueprint["theory_foundations"][0]["title"] == "输入假说"

    def test_blueprint_marks_no_theory(self):
        analysis = {"learner_gap": {"student_level": "A2", "gap": "", "gap_description": ""}}
        plan = {"activity_designs": []}
        wiki_results = []

        blueprint = build_teaching_blueprint(analysis, plan, wiki_results)

        assert blueprint["theory_foundations"] == []
        assert blueprint["objectives"] == []
