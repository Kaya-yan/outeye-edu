"""
句法分析器

基于Flesch-Kincaid和嵌套复杂度进行句法分析
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import re


@dataclass
class SyntacticAnalysisResult:
    """句法分析结果"""
    total_sentences: int
    total_words: int
    avg_sentence_length: float
    sentence_types: Dict[str, int]
    clause_density: float
    complexity_score: float
    flesch_kincaid_grade: float
    flesch_reading_ease: float


class SyntacticAnalyzer:
    """句法分析器"""

    def __init__(self):
        # 从句标记词
        self.subordinating_conjunctions = {
            'after', 'although', 'as', 'because', 'before', 'if', 'once',
            'since', 'than', 'that', 'though', 'till', 'until', 'when',
            'whenever', 'where', 'wherever', 'whether', 'while', 'unless'
        }

        # 关系代词
        self.relative_pronouns = {'who', 'whom', 'whose', 'which', 'that', 'where', 'when'}

        # 并列连词
        self.coordinating_conjunctions = {'and', 'but', 'or', 'nor', 'for', 'yet', 'so'}

    def analyze(self, text: str) -> SyntacticAnalysisResult:
        """
        分析句法

        Args:
            text: 文本内容

        Returns:
            句法分析结果
        """
        # 分割句子
        sentences = self._split_sentences(text)

        # 分词
        words = self._tokenize(text)

        # 统计基本指标
        total_sentences = len(sentences)
        total_words = len(words)
        avg_sentence_length = total_words / max(total_sentences, 1)

        # 分析句子类型
        sentence_types = self._analyze_sentence_types(sentences)

        # 计算从句密度
        clause_density = self._calculate_clause_density(sentences, total_sentences)

        # 计算Flesch-Kincaid指标
        syllable_count = self._count_syllables(words)
        flesch_kincaid_grade = self._calculate_flesch_kincaid_grade(
            total_words, total_sentences, syllable_count
        )
        flesch_reading_ease = self._calculate_flesch_reading_ease(
            total_words, total_sentences, syllable_count
        )

        # 计算复杂度评分
        complexity_score = self._calculate_complexity_score(
            avg_sentence_length, clause_density, sentence_types, total_sentences
        )

        return SyntacticAnalysisResult(
            total_sentences=total_sentences,
            total_words=total_words,
            avg_sentence_length=round(avg_sentence_length, 1),
            sentence_types=sentence_types,
            clause_density=round(clause_density, 2),
            complexity_score=round(complexity_score, 1),
            flesch_kincaid_grade=round(flesch_kincaid_grade, 1),
            flesch_reading_ease=round(flesch_reading_ease, 1)
        )

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        # 使用多种标点符号分割
        sentences = re.split(r'[.!?。！？]+', text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
        return sentences

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        text = text.lower()
        words = re.findall(r'[a-z]+', text)
        return [w for w in words if len(w) > 1]

    def _analyze_sentence_types(self, sentences: List[str]) -> Dict[str, int]:
        """分析句子类型"""
        types = {
            "simple": 0,  # 简单句
            "compound": 0,  # 并列句
            "complex": 0,  # 复合句
            "compound_complex": 0  # 并列复合句
        }

        for sentence in sentences:
            sentence_lower = sentence.lower()
            words = set(re.findall(r'[a-z]+', sentence_lower))

            # 检查是否有从句标记
            has_subordination = bool(
                words & self.subordinating_conjunctions or
                words & self.relative_pronouns
            )

            # 检查是否有并列结构
            has_coordination = bool(words & self.coordinating_conjunctions)

            # 分类
            if has_coordination and has_subordination:
                types["compound_complex"] += 1
            elif has_subordination:
                types["complex"] += 1
            elif has_coordination:
                types["compound"] += 1
            else:
                types["simple"] += 1

        return types

    def _calculate_clause_density(self, sentences: List[str], total_sentences: int) -> float:
        """计算从句密度"""
        if total_sentences == 0:
            return 0.0

        clause_count = 0
        for sentence in sentences:
            sentence_lower = sentence.lower()
            words = set(re.findall(r'[a-z]+', sentence_lower))

            # 计算从句数量
            subordinating_count = len(words & self.subordinating_conjunctions)
            relative_count = len(words & self.relative_pronouns)

            clause_count += subordinating_count + relative_count

        return clause_count / total_sentences

    def _count_syllables(self, words: List[str]) -> int:
        """统计音节数"""
        total_syllables = 0
        for word in words:
            total_syllables += self._count_word_syllables(word)
        return total_syllables

    def _count_word_syllables(self, word: str) -> int:
        """统计单词音节数"""
        word = word.lower()

        # 特殊情况
        if len(word) <= 3:
            return 1

        # 移除末尾的e
        if word.endswith('e'):
            word = word[:-1]

        # 统计元音组
        vowels = 'aeiouy'
        count = 0
        prev_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel

        return max(count, 1)

    def _calculate_flesch_kincaid_grade(
        self,
        total_words: int,
        total_sentences: int,
        total_syllables: int
    ) -> float:
        """计算Flesch-Kincaid年级水平"""
        if total_sentences == 0 or total_words == 0:
            return 0.0

        asl = total_words / total_sentences  # 平均句长
        asw = total_syllables / total_words  # 平均词长（音节）

        grade = 0.39 * asl + 11.8 * asw - 15.59

        return max(grade, 0)

    def _calculate_flesch_reading_ease(
        self,
        total_words: int,
        total_sentences: int,
        total_syllables: int
    ) -> float:
        """计算Flesch阅读容易度"""
        if total_sentences == 0 or total_words == 0:
            return 0.0

        asl = total_words / total_sentences  # 平均句长
        asw = total_syllables / total_words  # 平均词长（音节）

        ease = 206.835 - 1.015 * asl - 84.6 * asw

        return max(min(ease, 100), 0)

    def _calculate_complexity_score(
        self,
        avg_sentence_length: float,
        clause_density: float,
        sentence_types: Dict[str, int],
        total_sentences: int
    ) -> float:
        """计算复杂度评分"""
        # 句长因素（15-25词为正常范围）
        length_factor = min(max((avg_sentence_length - 10) / 20, 0), 1)

        # 从句密度因素
        density_factor = min(clause_density / 2, 1)

        # 句子类型因素
        if total_sentences > 0:
            complex_ratio = (sentence_types.get("complex", 0) +
                           sentence_types.get("compound_complex", 0)) / total_sentences
        else:
            complex_ratio = 0

        type_factor = min(complex_ratio * 2, 1)

        # 综合复杂度
        complexity = (length_factor * 0.4 + density_factor * 0.3 + type_factor * 0.3) * 10

        return min(max(complexity, 1), 10)
