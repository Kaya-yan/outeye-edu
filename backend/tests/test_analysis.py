"""
分析服务测试
"""

import pytest
from app.services.analysis.lexical_analyzer import LexicalAnalyzer
from app.services.analysis.syntactic_analyzer import SyntacticAnalyzer
from app.services.analysis.discourse_analyzer import DiscourseAnalyzer
from app.services.analysis.cognitive_load_analyzer import CognitiveLoadAnalyzer


class TestLexicalAnalyzer:
    """词汇分析器测试"""

    def setup_method(self):
        self.analyzer = LexicalAnalyzer()

    def test_basic_analysis(self):
        """测试基本分析功能"""
        text = "The quick brown fox jumps over the lazy dog. This is a simple sentence for testing."
        result = self.analyzer.analyze(text, "B1")

        assert result.total_words > 0
        assert result.unique_words > 0
        assert 0 < result.vocabulary_richness <= 1
        assert result.difficulty_score > 0

    def test_academic_words(self):
        """测试学术词汇识别"""
        text = "The hypothesis was tested through a comprehensive analysis of the research data."
        result = self.analyzer.analyze(text, "B1")

        assert result.academic_word_count > 0
        assert "hypothesis" in result.academic_words or "analysis" in result.academic_words

    def test_cefr_distribution(self):
        """测试CEFR分布"""
        text = "I have a good understanding of the theory and its applications."
        result = self.analyzer.analyze(text, "B1")

        assert "A1" in result.cefr_distribution
        assert sum(result.cefr_distribution.values()) > 0


class TestSyntacticAnalyzer:
    """句法分析器测试"""

    def setup_method(self):
        self.analyzer = SyntacticAnalyzer()

    def test_basic_analysis(self):
        """测试基本分析功能"""
        text = "The student read the book. She found it interesting because it was well-written."
        result = self.analyzer.analyze(text)

        assert result.total_sentences == 2
        assert result.total_words > 0
        assert result.avg_sentence_length > 0

    def test_sentence_types(self):
        """测试句子类型识别"""
        text = "I went to the store and bought some milk. Although it was raining, we went for a walk."
        result = self.analyzer.analyze(text)

        assert "simple" in result.sentence_types
        assert "complex" in result.sentence_types

    def test_flesch_kincaid(self):
        """测试Flesch-Kincaid指标"""
        text = "The quick brown fox jumps over the lazy dog. This is a test sentence."
        result = self.analyzer.analyze(text)

        assert result.flesch_kincaid_grade >= 0
        assert 0 <= result.flesch_reading_ease <= 100


class TestDiscourseAnalyzer:
    """语篇分析器测试"""

    def setup_method(self):
        self.analyzer = DiscourseAnalyzer()

    def test_basic_analysis(self):
        """测试基本分析功能"""
        text = """
        This is the first paragraph. It introduces the topic.

        This is the second paragraph. It provides more details.

        This is the third paragraph. It concludes the discussion.
        """
        result = self.analyzer.analyze(text)

        assert result.paragraph_count == 3
        assert result.coherence_score > 0

    def test_genre_identification(self):
        """测试体裁识别"""
        argumentative_text = """
        I believe that education is the key to success. However, some people argue that experience is more important.
        In my opinion, both are necessary. Therefore, we should balance education and experience.
        """
        result = self.analyzer.analyze(argumentative_text)

        assert result.genre_type == "argumentative"

    def test_cohesion_devices(self):
        """测试衔接手段分析"""
        text = "John went to the store. He bought some milk. Then he came home."
        result = self.analyzer.analyze(text)

        assert result.cohesion_devices["reference"] > 0


class TestCognitiveLoadAnalyzer:
    """认知负荷分析器测试"""

    def setup_method(self):
        self.analyzer = CognitiveLoadAnalyzer()

    def test_basic_analysis(self):
        """测试基本分析功能"""
        text = "This is a simple text for testing cognitive load analysis."
        result = self.analyzer.analyze(text, "B1")

        assert result.intrinsic_load > 0
        assert result.extraneous_load > 0
        assert result.germane_load > 0
        assert result.total_load > 0

    def test_overload_detection(self):
        """测试过载检测"""
        complex_text = """
        The quantum mechanical wave function describes the quantum state of a system.
        The Schrödinger equation is a partial differential equation that describes how
        the quantum state of a quantum physical system changes with time.
        """
        result = self.analyzer.analyze(complex_text, "A1")

        # 对于A1学生来说，这段文字应该有较高的认知负荷
        assert result.total_load > 5

    def test_recommendations(self):
        """测试建议生成"""
        text = "Simple test text."
        result = self.analyzer.analyze(text, "A1")

        assert isinstance(result.recommendations, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
