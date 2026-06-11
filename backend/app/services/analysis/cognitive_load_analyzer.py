"""
认知负荷分析器

基于认知负荷理论分析学习任务的认知负荷
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class CognitiveLoadResult:
    """认知负荷分析结果"""
    intrinsic_load: float  # 内在负荷
    extraneous_load: float  # 外在负荷
    germane_load: float  # 相关负荷
    total_load: float  # 总负荷
    overload: bool  # 是否过载
    recommendations: List[str]  # 建议


class CognitiveLoadAnalyzer:
    """认知负荷分析器"""

    def __init__(self):
        # 认知负荷因素权重
        self.weights = {
            "intrinsic": {
                "complexity": 0.4,
                "element_interactivity": 0.3,
                "prior_knowledge": 0.3
            },
            "extraneous": {
                "presentation_clarity": 0.4,
                "redundancy": 0.3,
                "split_attention": 0.3
            },
            "germane": {
                "schema_construction": 0.5,
                "schema_automation": 0.5
            }
        }

    def analyze(
        self,
        text: str,
        student_level: str = "B1",
        lexical_result=None,
        syntactic_result=None
    ) -> CognitiveLoadResult:
        """
        分析认知负荷

        Args:
            text: 文本内容
            student_level: 学生水平
            lexical_result: 词汇分析结果
            syntactic_result: 句法分析结果

        Returns:
            认知负荷分析结果
        """
        # 计算内在负荷
        intrinsic_load = self._calculate_intrinsic_load(
            text, student_level, lexical_result, syntactic_result
        )

        # 计算外在负荷
        extraneous_load = self._calculate_extraneous_load(text)

        # 计算相关负荷
        germane_load = self._calculate_germane_load(text, student_level)

        # 计算总负荷
        total_load = self._calculate_total_load(
            intrinsic_load, extraneous_load, germane_load
        )

        # 判断是否过载
        student_capacity = self._get_student_capacity(student_level)
        overload = total_load > student_capacity

        # 生成建议
        recommendations = self._generate_recommendations(
            intrinsic_load, extraneous_load, germane_load, total_load, overload, student_level
        )

        return CognitiveLoadResult(
            intrinsic_load=round(intrinsic_load, 1),
            extraneous_load=round(extraneous_load, 1),
            germane_load=round(germane_load, 1),
            total_load=round(total_load, 1),
            overload=overload,
            recommendations=recommendations
        )

    def _calculate_intrinsic_load(
        self,
        text: str,
        student_level: str,
        lexical_result,
        syntactic_result
    ) -> float:
        """计算内在负荷"""
        # 基于内容复杂度
        complexity_score = 5.0

        # 词汇复杂度
        if lexical_result:
            # 生词越多，复杂度越高
            unknown_ratio = len(lexical_result.unknown_words) / max(lexical_result.total_words, 1)
            complexity_score += unknown_ratio * 20

            # 学术词汇越多，复杂度越高
            academic_ratio = lexical_result.academic_word_count / max(lexical_result.total_words, 1)
            complexity_score += academic_ratio * 15

        # 句法复杂度
        if syntactic_result:
            complexity_score += syntactic_result.complexity_score * 0.5

        # 元素交互性（概念间的关联程度）
        element_interactivity = self._calculate_element_interactivity(text)

        # 先验知识匹配度
        prior_knowledge_factor = self._calculate_prior_knowledge_factor(
            text, student_level
        )

        # 综合内在负荷
        intrinsic_load = (
            complexity_score * self.weights["intrinsic"]["complexity"] +
            element_interactivity * self.weights["intrinsic"]["element_interactivity"] +
            (10 - prior_knowledge_factor) * self.weights["intrinsic"]["prior_knowledge"]
        )

        return min(max(intrinsic_load, 1), 10)

    def _calculate_element_interactivity(self, text: str) -> float:
        """计算元素交互性"""
        # 简化：基于概念密度和关联词
        words = text.lower().split()

        # 检查逻辑连接词
        logical_connectors = [
            'because', 'therefore', 'however', 'although', 'if', 'then',
            'while', 'unless', 'since', 'as', 'so', 'but', 'and', 'or'
        ]

        connector_count = sum(1 for w in words if w in logical_connectors)
        connector_density = connector_count / max(len(words), 1) * 100

        # 检查复杂概念
        complex_concepts = [
            'theory', 'hypothesis', 'concept', 'framework', 'model',
            'analysis', 'synthesis', 'evaluation', 'comparison', 'contrast'
        ]

        concept_count = sum(1 for w in words if w in complex_concepts)
        concept_density = concept_count / max(len(words), 1) * 100

        # 综合交互性
        interactivity = min(connector_density * 2 + concept_density * 3, 10)

        return interactivity

    def _calculate_prior_knowledge_factor(self, text: str, student_level: str) -> float:
        """计算先验知识匹配度"""
        # 基于学生水平和文本难度的匹配
        level_values = {
            "A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6
        }

        student_value = level_values.get(student_level, 3)

        # 简化：基于词汇难度估算文本水平
        words = text.lower().split()
        # 假设平均词汇水平约为B1（3）
        text_level_estimate = 3.5

        # 匹配度
        level_diff = abs(text_level_estimate - student_value)
        match_factor = max(10 - level_diff * 2, 0)

        return match_factor

    def _calculate_extraneous_load(self, text: str) -> float:
        """计算外在负荷"""
        # 基于呈现方式的清晰度
        clarity_score = self._assess_presentation_clarity(text)

        # 冗余度
        redundancy_score = self._assess_redundancy(text)

        # 分散注意力
        split_attention_score = self._assess_split_attention(text)

        # 综合外在负荷
        extraneous_load = (
            (10 - clarity_score) * self.weights["extraneous"]["presentation_clarity"] +
            redundancy_score * self.weights["extraneous"]["redundancy"] +
            split_attention_score * self.weights["extraneous"]["split_attention"]
        )

        return min(max(extraneous_load, 1), 10)

    def _assess_presentation_clarity(self, text: str) -> float:
        """评估呈现清晰度"""
        # 基于段落结构
        paragraphs = text.split('\n\n')
        paragraph_count = len([p for p in paragraphs if p.strip()])

        # 基于句子长度一致性
        sentences = text.split('.')
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]

        if sentence_lengths:
            avg_length = sum(sentence_lengths) / len(sentence_lengths)
            length_variance = sum((l - avg_length) ** 2 for l in sentence_lengths) / len(sentence_lengths)
            consistency = max(10 - length_variance / 10, 0)
        else:
            consistency = 5

        # 综合清晰度
        clarity = min(paragraph_count * 2 + consistency * 0.5, 10)

        return clarity

    def _assess_redundancy(self, text: str) -> float:
        """评估冗余度"""
        words = text.lower().split()

        # 统计词频
        word_freq = {}
        for word in words:
            if len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1

        # 计算重复率
        if not word_freq:
            return 5.0

        repeated_words = sum(1 for freq in word_freq.values() if freq > 3)
        redundancy = repeated_words / len(word_freq) * 10

        return min(redundancy, 10)

    def _assess_split_attention(self, text: str) -> float:
        """评估分散注意力"""
        # 检查是否有需要整合的信息
        # 简化：基于引用和参照
        import re

        references = re.findall(r'\b(this|that|these|those|such)\b', text, re.IGNORECASE)
        reference_density = len(references) / max(len(text.split()), 1) * 100

        # 检查括号、脚注等
        parentheses = text.count('(')
        footnotes = text.count('[')

        split_attention = reference_density * 2 + (parentheses + footnotes) * 0.5

        return min(split_attention, 10)

    def _calculate_germane_load(self, text: str, student_level: str) -> float:
        """计算相关负荷"""
        # 相关负荷是学习者用于构建图式的认知资源
        # 适当的相关负荷是有利于学习的

        # 基于内容的组织结构
        structure_score = self._assess_content_structure(text)

        # 基于学习目标的明确性
        objective_score = self._assess_learning_objectives(text)

        # 综合相关负荷
        germane_load = (
            structure_score * self.weights["germane"]["schema_construction"] +
            objective_score * self.weights["germane"]["schema_automation"]
        )

        return min(max(germane_load, 1), 10)

    def _assess_content_structure(self, text: str) -> float:
        """评估内容结构"""
        # 检查是否有清晰的结构标记
        structure_markers = [
            'first', 'second', 'third', 'finally', 'in conclusion',
            'for example', 'for instance', 'in addition', 'moreover',
            'however', 'on the other hand', 'in contrast'
        ]

        text_lower = text.lower()
        marker_count = sum(1 for marker in structure_markers if marker in text_lower)

        # 段落结构
        paragraphs = text.split('\n\n')
        paragraph_count = len([p for p in paragraphs if p.strip()])

        structure_score = min(marker_count * 1.5 + paragraph_count, 10)

        return structure_score

    def _assess_learning_objectives(self, text: str) -> float:
        """评估学习目标明确性"""
        # 检查是否有目标相关词汇
        objective_markers = [
            'objective', 'goal', 'aim', 'purpose', 'learn', 'understand',
            'be able to', 'should', 'must', 'will learn', 'by the end'
        ]

        text_lower = text.lower()
        marker_count = sum(1 for marker in objective_markers if marker in text_lower)

        objective_score = min(marker_count * 2, 10)

        return objective_score

    def _calculate_total_load(
        self,
        intrinsic: float,
        extraneous: float,
        germane: float
    ) -> float:
        """计算总负荷"""
        # 总负荷 = 内在负荷 + 外在负荷
        # 相关负荷是正面的，不计入总负荷
        total = intrinsic + extraneous

        return min(max(total, 1), 10)

    def _get_student_capacity(self, student_level: str) -> float:
        """获取学生认知容量"""
        # 不同水平学生的认知容量
        capacity_map = {
            "A1": 5.0,
            "A2": 5.5,
            "B1": 6.0,
            "B2": 6.5,
            "C1": 7.0,
            "C2": 7.5
        }

        return capacity_map.get(student_level, 6.0)

    def _generate_recommendations(
        self,
        intrinsic: float,
        extraneous: float,
        germane: float,
        total: float,
        overload: bool,
        student_level: str
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        # 基于内在负荷
        if intrinsic > 7:
            recommendations.append("内容复杂度较高，建议分步讲解或提供预习材料")
            recommendations.append("可以使用图表、示例等方式简化复杂概念")

        # 基于外在负荷
        if extraneous > 6:
            recommendations.append("呈现方式可能增加认知负荷，建议优化内容组织")
            recommendations.append("减少冗余信息，突出重点内容")

        # 基于相关负荷
        if germane < 4:
            recommendations.append("内容结构不够清晰，建议增加结构标记和过渡")
            recommendations.append("明确学习目标，帮助学生构建知识图式")

        # 基于总负荷
        if overload:
            recommendations.append("认知负荷过高，存在过载风险")
            recommendations.append("建议提供支架支持或降低任务难度")
            recommendations.append("可以将复杂任务分解为小步骤")

        # 基于学生水平
        if student_level in ["A1", "A2"] and total > 5:
            recommendations.append("初级学习者认知容量有限，建议简化内容或提供更多支持")

        return recommendations
