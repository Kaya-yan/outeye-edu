"""
可追溯证据引用测试（TDD）

目标：
1. 有匹配证据时，为活动/建议绑定引用来源
2. 无匹配证据时，显式标记 degraded（不静默生成无据内容）
"""

import pytest

from app.services.analysis.citation import (
    normalize_evidence,
    bind_evidence_to_section,
    annotate_plan,
)


def make_evidence():
    wiki = [
        {"title": "输入假说", "summary": "可理解输入 i+1 理论", "relevance_score": 0.9},
        {"title": "认知负荷理论", "summary": "降低外在负荷", "relevance_score": 0.8},
    ]
    rag = [
        {"content": "词汇预习活动设计", "metadata": {"title": "词汇教学资源"}, "score": 0.85},
        {"content": "写作仿写练习", "metadata": {"title": "写作活动"}, "score": 0.7},
    ]
    return wiki, rag


class TestNormalizeEvidence:
    """证据归一化测试"""

    def test_normalize_combines_wiki_and_rag(self):
        wiki, rag = make_evidence()
        evidence = normalize_evidence(wiki, rag)

        assert len(evidence) == 4
        assert evidence[0]["source_type"] == "wiki"
        assert evidence[2]["source_type"] == "rag"


class TestBindEvidenceToSection:
    """证据绑定测试"""

    def test_binds_matching_evidence(self):
        """有匹配证据时应绑定引用"""
        wiki, rag = make_evidence()
        evidence = normalize_evidence(wiki, rag)

        section_text = "基于输入假说设计词汇预习活动"
        result = bind_evidence_to_section(section_text, evidence)

        assert result["degraded"] is False
        assert len(result["citations"]) > 0
        # 应命中"输入假说"或"词汇"
        titles = [c["title"] for c in result["citations"]]
        assert any("输入假说" in t or "词汇" in t for t in titles)

    def test_marks_degraded_when_no_match(self):
        """无匹配证据时应显式标记 degraded"""
        wiki, rag = make_evidence()
        evidence = normalize_evidence(wiki, rag)

        section_text = "关于音乐旋律与和弦的讨论"
        result = bind_evidence_to_section(section_text, evidence)

        assert result["degraded"] is True
        assert result["citations"] == []


class TestAnnotatePlan:
    """整体教案证据标注测试"""

    def test_annotate_plan_adds_evidence_fields(self):
        wiki, rag = make_evidence()
        plan = {
            "difficulty_overview": "课文难度概述",
            "teaching_suggestions": ["基于输入假说的建议", "无关建议内容"],
            "activity_designs": [
                {"name": "词汇预习活动", "steps": "1. 预习词汇"},
                {"name": "音乐旋律活动", "steps": "1. 讲解旋律"},
            ],
        }

        annotated = annotate_plan(plan, wiki, rag)

        # 建议应带 evidence 字段
        assert "evidence" in annotated["teaching_suggestions"][0]
        # 活动应带 evidence 字段
        for activity in annotated["activity_designs"]:
            assert "evidence" in activity
            assert "degraded" in activity
