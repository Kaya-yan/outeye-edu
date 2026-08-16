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

    def test_blueprint_stages_distribute_activities(self):
        """5 个活动应分布到 5 个阶段"""
        activities = [{"name": f"a{i}", "objective": f"o{i}"} for i in range(1, 6)]
        blueprint = build_teaching_blueprint({}, {"activity_designs": activities}, [])

        assert len(blueprint["stages"]) == 5
        assert blueprint["stages"][0]["stage"] == "导入"
        assert blueprint["stages"][-1]["stage"] == "总结"

    def test_blueprint_filters_empty_stages(self):
        """3 个活动只显示 3 个阶段（检测/总结留空）"""
        activities = [{"name": "a1"}, {"name": "a2"}, {"name": "a3"}]
        blueprint = build_teaching_blueprint({}, {"activity_designs": activities}, [])

        assert len(blueprint["stages"]) == 3

    def test_blueprint_time_budget(self):
        """时间预算总时长应等于 duration_minutes"""
        activities = [{"name": "a1"}, {"name": "a2"}, {"name": "a3"}]
        blueprint = build_teaching_blueprint(
            {}, {"activity_designs": activities}, [], [], duration_minutes=90
        )

        tb = blueprint["time_budget"]
        assert tb["total_minutes"] == 90
        assert sum(a["minutes"] for a in tb["activities"]) == 90

    def test_blueprint_evidence_types(self):
        """关键证据类型应按 wiki/rag 计数"""
        blueprint = build_teaching_blueprint(
            {}, {"activity_designs": []},
            [{"title": "w"}], [{"content": "r"}],
        )

        assert blueprint["evidence_types"]["theory"] == 1
        assert blueprint["evidence_types"]["resource"] == 1

    def test_blueprint_evaluation_points(self):
        """评价点应从活动目标派生"""
        activities = [{"name": "词汇", "objective": "掌握新词"}]
        blueprint = build_teaching_blueprint(
            {"learner_gap": {"gap": "i+1", "gap_description": "略高"}},
            {"activity_designs": activities},
            [],
        )

        assert len(blueprint["evaluation_points"]) >= 1
