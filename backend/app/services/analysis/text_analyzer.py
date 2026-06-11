"""
智能课文分析引擎

整合多维度分析功能，提供全面的课文分析
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from .lexical_analyzer import LexicalAnalyzer, LexicalAnalysisResult
from .syntactic_analyzer import SyntacticAnalyzer, SyntacticAnalysisResult
from .discourse_analyzer import DiscourseAnalyzer, DiscourseAnalysisResult
from .cognitive_load_analyzer import CognitiveLoadAnalyzer, CognitiveLoadResult


@dataclass
class TextAnalysisResult:
    """课文分析结果"""
    text_id: str
    title: str
    lexical: LexicalAnalysisResult
    syntactic: SyntacticAnalysisResult
    discourse: DiscourseAnalysisResult
    cognitive_load: CognitiveLoadResult
    overall_difficulty: float
    cefr_level: str
    teaching_suggestions: List[str]
    analysis_summary: str


class TextAnalyzer:
    """智能课文分析引擎"""

    def __init__(self):
        self.lexical_analyzer = LexicalAnalyzer()
        self.syntactic_analyzer = SyntacticAnalyzer()
        self.discourse_analyzer = DiscourseAnalyzer()
        self.cognitive_load_analyzer = CognitiveLoadAnalyzer()

    def analyze(
        self,
        text: str,
        title: str = "",
        student_level: str = "B1",
        learning_objectives: Optional[List[str]] = None
    ) -> TextAnalysisResult:
        """
        综合分析课文

        Args:
            text: 课文内容
            title: 课文标题
            student_level: 学生水平（CEFR）
            learning_objectives: 学习目标

        Returns:
            分析结果
        """
        import hashlib
        text_id = hashlib.md5(text.encode()).hexdigest()[:16]

        # 词汇分析
        lexical_result = self.lexical_analyzer.analyze(text, student_level)

        # 句法分析
        syntactic_result = self.syntactic_analyzer.analyze(text)

        # 语篇分析
        discourse_result = self.discourse_analyzer.analyze(text)

        # 认知负荷分析
        cognitive_load_result = self.cognitive_load_analyzer.analyze(
            text, student_level, lexical_result, syntactic_result
        )

        # 计算整体难度
        overall_difficulty = self._calculate_overall_difficulty(
            lexical_result, syntactic_result, discourse_result, cognitive_load_result
        )

        # 确定CEFR等级
        cefr_level = self._determine_cefr_level(overall_difficulty)

        # 生成教学建议
        teaching_suggestions = self._generate_teaching_suggestions(
            lexical_result, syntactic_result, discourse_result,
            cognitive_load_result, student_level
        )

        # 生成分析摘要
        analysis_summary = self._generate_analysis_summary(
            lexical_result, syntactic_result, discourse_result,
            cognitive_load_result, overall_difficulty, cefr_level
        )

        return TextAnalysisResult(
            text_id=text_id,
            title=title,
            lexical=lexical_result,
            syntactic=syntactic_result,
            discourse=discourse_result,
            cognitive_load=cognitive_load_result,
            overall_difficulty=overall_difficulty,
            cefr_level=cefr_level,
            teaching_suggestions=teaching_suggestions,
            analysis_summary=analysis_summary
        )

    def _calculate_overall_difficulty(
        self,
        lexical: LexicalAnalysisResult,
        syntactic: SyntacticAnalysisResult,
        discourse: DiscourseAnalysisResult,
        cognitive_load: CognitiveLoadResult
    ) -> float:
        """计算整体难度"""
        # 词汇难度（基于CEFR分布）
        lexical_difficulty = lexical.difficulty_score

        # 句法难度
        syntactic_difficulty = syntactic.complexity_score

        # 语篇难度
        discourse_difficulty = 10 - discourse.coherence_score

        # 认知负荷
        cognitive_difficulty = cognitive_load.total_load

        # 综合难度（加权平均）
        overall = (
            lexical_difficulty * 0.35 +
            syntactic_difficulty * 0.25 +
            discourse_difficulty * 0.20 +
            cognitive_difficulty * 0.20
        )

        return round(min(max(overall, 1), 10), 1)

    def _determine_cefr_level(self, difficulty: float) -> str:
        """根据难度确定CEFR等级"""
        if difficulty <= 2:
            return "A1"
        elif difficulty <= 3.5:
            return "A2"
        elif difficulty <= 5:
            return "B1"
        elif difficulty <= 6.5:
            return "B2"
        elif difficulty <= 8:
            return "C1"
        else:
            return "C2"

    def _generate_teaching_suggestions(
        self,
        lexical: LexicalAnalysisResult,
        syntactic: SyntacticAnalysisResult,
        discourse: DiscourseAnalysisResult,
        cognitive_load: CognitiveLoadResult,
        student_level: str
    ) -> List[str]:
        """生成教学建议"""
        suggestions = []

        # 词汇建议
        if len(lexical.unknown_words) > 10:
            suggestions.append(f"课文包含{len(lexical.unknown_words)}个可能的生词，建议预教关键词汇")

        if lexical.academic_word_count > 5:
            suggestions.append(f"课文包含{lexical.academic_word_count}个学术词汇，建议设计词汇扩展活动")

        # 句法建议
        if syntactic.complexity_score > 7:
            suggestions.append("句法复杂度较高，建议分析复杂句结构")

        if syntactic.avg_sentence_length > 25:
            suggestions.append("平均句长较长，建议进行句法分析练习")

        # 语篇建议
        if discourse.coherence_score < 6:
            suggestions.append("语篇连贯性有待提高，建议分析衔接手段")

        if discourse.genre_type:
            suggestions.append(f"课文为{discourse.genre_type}体裁，建议分析体裁结构")

        # 认知负荷建议
        if cognitive_load.overload:
            suggestions.append("认知负荷过高，建议提供支架支持或降低任务难度")

        if cognitive_load.intrinsic_load > 7:
            suggestions.append("内容难度较高，建议分步讲解或提供预习材料")

        # 基于学生水平的建议
        level_hierarchy = ["A1", "A2", "B1", "B2", "C1", "C2"]
        if student_level in level_hierarchy:
            student_idx = level_hierarchy.index(student_level)
            text_level = self._determine_cefr_level(
                (lexical.difficulty_score + syntactic.complexity_score) / 2
            )
            if text_level in level_hierarchy:
                text_idx = level_hierarchy.index(text_level)

                if text_idx > student_idx + 1:
                    suggestions.append("课文难度明显高于学生水平，建议提供充分的预习和支架")
                elif text_idx < student_idx - 1:
                    suggestions.append("课文难度低于学生水平，可以增加拓展学习内容")

        return suggestions

    def _generate_analysis_summary(
        self,
        lexical: LexicalAnalysisResult,
        syntactic: SyntacticAnalysisResult,
        discourse: DiscourseAnalysisResult,
        cognitive_load: CognitiveLoadResult,
        overall_difficulty: float,
        cefr_level: str
    ) -> str:
        """生成分析摘要"""
        summary = f"本课文整体难度为{overall_difficulty}/10，对应CEFR {cefr_level}等级。\n\n"

        # 词汇方面
        summary += f"词汇方面：共{lexical.total_words}个词，"
        summary += f"词汇丰富度{lexical.vocabulary_richness:.1%}，"
        summary += f"包含{lexical.academic_word_count}个学术词汇。\n"

        # 句法方面
        summary += f"句法方面：共{syntactic.total_sentences}个句子，"
        summary += f"平均句长{syntactic.avg_sentence_length:.1f}词，"
        summary += f"句法复杂度{syntactic.complexity_score}/10。\n"

        # 语篇方面
        summary += f"语篇方面：连贯性评分{discourse.coherence_score}/10"
        if discourse.genre_type:
            summary += f"，体裁类型为{discourse.genre_type}"
        summary += "。\n"

        # 认知负荷
        summary += f"认知负荷：总负荷{cognitive_load.total_load}/10"
        if cognitive_load.overload:
            summary += "（存在过载风险）"
        summary += "。"

        return summary

    def generate_detailed_report(
        self,
        result: TextAnalysisResult
    ) -> Dict[str, Any]:
        """
        生成详细分析报告

        Args:
            result: 分析结果

        Returns:
            详细报告
        """
        return {
            "基本信息": {
                "文本ID": result.text_id,
                "标题": result.title,
                "整体难度": result.overall_difficulty,
                "CEFR等级": result.cefr_level
            },
            "词汇分析": {
                "总词数": result.lexical.total_words,
                "独特词数": result.lexical.unique_words,
                "词汇丰富度": round(result.lexical.vocabulary_richness, 3),
                "学术词汇数": result.lexical.academic_word_count,
                "生词列表": result.lexical.unknown_words[:20],
                "难度评分": result.lexical.difficulty_score
            },
            "句法分析": {
                "总句数": result.syntactic.total_sentences,
                "平均句长": round(result.syntactic.avg_sentence_length, 1),
                "句子类型分布": result.syntactic.sentence_types,
                "从句密度": round(result.syntactic.clause_density, 2),
                "复杂度评分": result.syntactic.complexity_score
            },
            "语篇分析": {
                "连贯性评分": result.discourse.coherence_score,
                "体裁类型": result.discourse.genre_type,
                "衔接手段": result.discourse.cohesion_devices,
                "主位推进模式": result.discourse.thematic_progression
            },
            "认知负荷": {
                "内在负荷": result.cognitive_load.intrinsic_load,
                "外在负荷": result.cognitive_load.extraneous_load,
                "相关负荷": result.cognitive_load.germane_load,
                "总负荷": result.cognitive_load.total_load,
                "是否过载": result.cognitive_load.overload
            },
            "教学建议": result.teaching_suggestions,
            "分析摘要": result.analysis_summary
        }
