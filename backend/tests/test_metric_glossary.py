"""任务F1 术语表测试：分档解读实例化 / 全条目完整性 / /whitebox 响应携带 metric_glossary"""

import pytest

from app.main import app
from app.core.security import get_current_user
from app.services.analysis.metric_glossary import METRICS, build_glossary
from app.services.analysis.whitebox_analyzer import WhiteboxAnalyzer


class TestMetricSpec:
    def test_awl_band_daily(self):
        # 1.4% 落在 <3% 档：日常叙事
        text = METRICS["AWL 占比"].interpret(0.014)
        assert text is not None and "1.4%" in text and "日常叙事" in text

    def test_awl_band_high_academic(self):
        text = METRICS["AWL 占比"].interpret(0.09)
        assert text is not None and "预习" in text

    def test_flesch_band_hard(self):
        text = METRICS["可读性指数"].interpret(25)
        assert text is not None and "很难" in text

    def test_flesch_band_easy(self):
        text = METRICS["可读性指数"].interpret(75)
        assert text is not None and "极易" in text

    def test_connective_band(self):
        assert "/百词" in METRICS["连接密度"].interpret(5.0)

    def test_non_numeric_returns_none(self):
        assert METRICS["体裁"].interpret("argumentative") is None


class TestBuildGlossary:
    def setup_method(self):
        self.analyzer = WhiteboxAnalyzer()
        self.text = (
            "This is the story of a sturdy American symbol which has now spread throughout most of the world. "
            "Blue jeans are favored equally by bureaucrats and cowboys. "
            "However, their origins are humble: they were stitched by a peddler named Levi Strauss."
        )
        self.glossary = build_glossary(self.analyzer.analyze(self.text, "B2"))

    def test_all_entries_have_name_definition_teaching(self):
        assert len(self.glossary) >= 15
        for key, entry in self.glossary.items():
            assert entry["name"], key
            assert entry["definition"], key
            assert entry["teaching"], key

    def test_awl_interpretation_instantiated_with_text_value(self):
        awl = self.glossary["AWL 占比"]
        assert "interpretation" in awl and "%" in awl["interpretation"]

    def test_genre_override_mentions_label(self):
        genre = self.glossary["体裁"]
        assert "本文判定为" in genre["interpretation"]

    def test_cefr_override_has_percentages(self):
        cefr = self.glossary["CEFR 词汇分布"]
        assert "A1-A2" in cefr["interpretation"] and "%" in cefr["interpretation"]

    def test_aliases_share_readability(self):
        assert self.glossary["Flesch"]["interpretation"] == self.glossary["可读性"]["interpretation"] == self.glossary["可读性指数"]["interpretation"]

    def test_readability_index_instantiated(self):
        entry = self.glossary["可读性指数"]
        assert "本文" in entry["interpretation"]


class TestWhiteboxEndpoint:
    def test_response_contains_metric_glossary(self, client, monkeypatch):
        # 白盒端点会写 analysis_records，必须走 conftest client（内存库 get_async_db override）
        async def override_auth():
            return {"user_id": "user-1", "email": "test@example.com", "is_admin": False}

        app.dependency_overrides[get_current_user] = override_auth

        # F4.3 兜底分级在 LLM 不可用时降级返回，不影响本测试关注点
        async def _no_grading(*a, **k):
            return {}, {"fallback": True}

        monkeypatch.setattr(
            "app.services.analysis.word_grader.grade_ungraded_words", _no_grading
        )
        res = client.post(
            "/api/v1/analysis/whitebox",
            json={
                "text": "Blue jeans are favored equally by bureaucrats and cowboys. However, their origins are humble.",
                "title": "词汇测试课文",
                "student_level": "B2",
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["fallback_used"] is False
        gl = body["metric_glossary"]
        assert gl["AWL 占比"]["interpretation"]
        assert "本文" in gl["可读性指数"]["interpretation"]
        assert gl["体裁"]["name"] == "体裁"
