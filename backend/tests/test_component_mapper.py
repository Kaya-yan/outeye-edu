"""
组件库驱动课件映射测试（TDD）

目标：教案各节应映射到官方教学组件（ComponentDefinition），而非硬编码 HTML 块。
"""

import pytest

from app.services.analysis.component_mapper import resolve_component_for_section


def make_components():
    return [
        {
            "slug": "vocab-card", "name": "词汇讲解卡", "category": "知识讲授",
            "teaching_stage": "讲授", "subject_tags": ["词汇教学"],
            "render_template_html": "<div>vocab</div>",
        },
        {
            "slug": "group-discussion", "name": "小组讨论任务卡", "category": "活动组织",
            "teaching_stage": "活动", "subject_tags": ["小组讨论"],
            "render_template_html": "<div>discussion</div>",
        },
        {
            "slug": "summary-page", "name": "本课总结页", "category": "总结反思",
            "teaching_stage": "总结", "subject_tags": ["课堂总结"],
            "render_template_html": "<div>summary</div>",
        },
    ]


class TestResolveComponentForSection:
    """组件映射测试"""

    def test_matches_component_by_stage_and_keyword(self):
        components = make_components()

        # 活动阶段 + "讨论"关键词 → group-discussion
        result = resolve_component_for_section("活动", "小组讨论任务", components)
        assert result is not None
        assert result["slug"] == "group-discussion"

    def test_matches_vocab_component(self):
        components = make_components()

        result = resolve_component_for_section("讲授", "词汇讲解", components)
        assert result is not None
        assert result["slug"] == "vocab-card"

    def test_returns_none_when_no_match(self):
        components = make_components()

        result = resolve_component_for_section("活动", "量子物理实验", components)
        assert result is None
