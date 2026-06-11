"""
语篇分析器

分析语篇连贯性、体裁结构和信息流
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import re


@dataclass
class DiscourseAnalysisResult:
    """语篇分析结果"""
    coherence_score: float
    genre_type: str
    cohesion_devices: Dict[str, int]
    thematic_progression: str
    paragraph_count: int
    avg_paragraph_length: float
    topic_consistency: float


class DiscourseAnalyzer:
    """语篇分析器"""

    def __init__(self):
        # 体裁关键词
        self.genre_keywords = {
            "argumentative": [
                "argue", "claim", "assert", "contend", "believe", "think",
                "opinion", "view", "perspective", "however", "although",
                "but", "despite", "nevertheless", "on the other hand",
                "in conclusion", "therefore", "thus", "hence"
            ],
            "expository": [
                "explain", "describe", "define", "illustrate", "demonstrate",
                "for example", "for instance", "such as", "specifically",
                "in other words", "that is", "namely", "first", "second",
                "third", "finally", "in conclusion", "to summarize"
            ],
            "narrative": [
                "once upon a time", "one day", "suddenly", "then", "next",
                "finally", "in the end", "at first", "meanwhile", "later",
                "before", "after", "when", "while", "as soon as"
            ],
            "descriptive": [
                "beautiful", "ugly", "large", "small", "bright", "dark",
                "loud", "quiet", "soft", "hard", "looks like", "appears",
                "seems", "resembles", "reminds", "color", "shape", "size"
            ],
            "scientific": [
                "hypothesis", "experiment", "theory", "evidence", "data",
                "results", "conclusion", "method", "analysis", "observe",
                "measure", "calculate", "determine", "investigate", "research"
            ]
        }

        # 衔接手段
        self.cohesion_markers = {
            "reference": [
                r'\b(he|she|it|they|we|I|you)\b',
                r'\b(this|that|these|those)\b',
                r'\b(his|her|its|their|our|my|your)\b',
                r'\b(himself|herself|itself|themselves|ourselves|myself)\b'
            ],
            "conjunction": [
                r'\b(and|but|or|yet|so|nor)\b',
                r'\b(however|therefore|moreover|furthermore|consequently)\b',
                r'\b(because|although|when|if|while|since|unless)\b',
                r'\b(first|second|third|finally|next|then)\b',
                r'\b(for example|for instance|such as|specifically)\b',
                r'\b(in addition|in contrast|on the other hand|similarly)\b'
            ],
            "lexical_cohesion": [
                # 同义词/近义词（简化：使用重复词检测）
                r'\b(\w+)\b.*\b\1\b'  # 重复词
            ]
        }

    def analyze(self, text: str) -> DiscourseAnalysisResult:
        """
        分析语篇

        Args:
            text: 文本内容

        Returns:
            语篇分析结果
        """
        # 分割段落
        paragraphs = self._split_paragraphs(text)

        # 分割句子
        sentences = self._split_sentences(text)

        # 识别体裁
        genre_type = self._identify_genre(text)

        # 分析衔接手段
        cohesion_devices = self._analyze_cohesion(text)

        # 计算连贯性评分
        coherence_score = self._calculate_coherence_score(
            text, sentences, paragraphs, cohesion_devices
        )

        # 分析主位推进
        thematic_progression = self._analyze_thematic_progression(sentences)

        # 计算主题一致性
        topic_consistency = self._calculate_topic_consistency(sentences)

        # 计算平均段落长度
        avg_paragraph_length = sum(len(p.split()) for p in paragraphs) / max(len(paragraphs), 1)

        return DiscourseAnalysisResult(
            coherence_score=round(coherence_score, 1),
            genre_type=genre_type,
            cohesion_devices=cohesion_devices,
            thematic_progression=thematic_progression,
            paragraph_count=len(paragraphs),
            avg_paragraph_length=round(avg_paragraph_length, 1),
            topic_consistency=round(topic_consistency, 1)
        )

    def _split_paragraphs(self, text: str) -> List[str]:
        """分割段落"""
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 10]
        return paragraphs

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        sentences = re.split(r'[.!?。！？]+', text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
        return sentences

    def _identify_genre(self, text: str) -> str:
        """识别体裁"""
        text_lower = text.lower()

        # 计算每种体裁的匹配分数
        genre_scores = {}
        for genre, keywords in self.genre_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            genre_scores[genre] = score

        # 选择得分最高的体裁
        if not genre_scores or max(genre_scores.values()) == 0:
            return "unknown"

        return max(genre_scores.items(), key=lambda x: x[1])[0]

    def _analyze_cohesion(self, text: str) -> Dict[str, int]:
        """分析衔接手段"""
        cohesion = {
            "reference": 0,
            "conjunction": 0,
            "lexical_cohesion": 0
        }

        # 参照
        for pattern in self.cohesion_markers["reference"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            cohesion["reference"] += len(matches)

        # 连接
        for pattern in self.cohesion_markers["conjunction"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            cohesion["conjunction"] += len(matches)

        # 词汇衔接（简化：检测重复词）
        words = re.findall(r'\b[a-z]+\b', text.lower())
        word_freq = {}
        for word in words:
            if len(word) > 3:  # 忽略短词
                word_freq[word] = word_freq.get(word, 0) + 1

        # 统计重复词
        repeated_words = sum(1 for freq in word_freq.values() if freq > 1)
        cohesion["lexical_cohesion"] = repeated_words

        return cohesion

    def _calculate_coherence_score(
        self,
        text: str,
        sentences: List[str],
        paragraphs: List[str],
        cohesion_devices: Dict[str, int]
    ) -> float:
        """计算连贯性评分"""
        if not sentences:
            return 0.0

        # 衔接手段密度
        total_cohesion = sum(cohesion_devices.values())
        word_count = len(text.split())
        cohesion_density = total_cohesion / max(word_count, 1) * 100

        # 段落结构
        paragraph_score = min(len(paragraphs) / 3, 1) * 10  # 至少3段得满分

        # 句子长度一致性
        sentence_lengths = [len(s.split()) for s in sentences]
        if sentence_lengths:
            avg_length = sum(sentence_lengths) / len(sentence_lengths)
            length_variance = sum((l - avg_length) ** 2 for l in sentence_lengths) / len(sentence_lengths)
            length_consistency = max(1 - length_variance / 100, 0) * 10
        else:
            length_consistency = 5

        # 综合连贯性
        coherence = (
            min(cohesion_density, 10) * 0.4 +
            paragraph_score * 0.3 +
            length_consistency * 0.3
        )

        return min(max(coherence, 1), 10)

    def _analyze_thematic_progression(self, sentences: List[str]) -> str:
        """分析主位推进模式"""
        if len(sentences) < 2:
            return "insufficient_data"

        # 提取每个句子的主位（简化：取前几个词）
        themes = []
        for sentence in sentences[:10]:  # 分析前10句
            words = sentence.split()[:3]  # 取前3个词作为主位
            themes.append(' '.join(words).lower())

        # 分析推进模式
        # 平行推进：主位相同
        parallel_count = 0
        for i in range(1, len(themes)):
            if themes[i][:10] == themes[i-1][:10]:  # 简单比较
                parallel_count += 1

        # 线性推进：前句述位成为后句主位
        linear_count = 0
        for i in range(1, len(sentences)):
            prev_words = set(sentences[i-1].lower().split()[-3:])  # 前句最后3词
            curr_words = set(sentences[i].lower().split()[:3])  # 后句前3词
            if prev_words & curr_words:
                linear_count += 1

        # 判断主要模式
        if parallel_count > len(themes) * 0.3:
            return "parallel"
        elif linear_count > len(sentences) * 0.3:
            return "linear"
        else:
            return "mixed"

    def _calculate_topic_consistency(self, sentences: List[str]) -> float:
        """计算主题一致性"""
        if len(sentences) < 2:
            return 10.0

        # 提取关键词（简化：使用高频词）
        all_words = []
        for sentence in sentences:
            words = re.findall(r'\b[a-z]+\b', sentence.lower())
            all_words.extend([w for w in words if len(w) > 3])

        # 统计词频
        word_freq = {}
        for word in all_words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # 获取高频词作为主题词
        if not word_freq:
            return 5.0

        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        topic_words = set(w for w, f in sorted_words[:10])

        # 计算每个句子与主题词的重叠
        consistency_scores = []
        for sentence in sentences:
            words = set(re.findall(r'\b[a-z]+\b', sentence.lower()))
            overlap = len(words & topic_words)
            consistency_scores.append(overlap / max(len(words), 1))

        # 平均一致性
        avg_consistency = sum(consistency_scores) / len(consistency_scores)

        # 转换为0-10评分
        return min(avg_consistency * 50, 10)
