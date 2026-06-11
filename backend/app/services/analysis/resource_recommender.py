"""
教学资源推荐模块

基于RAG和Wiki推荐教学资源
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ResourceRecommendation:
    """资源推荐"""
    resource_type: str  # literature, courseware, exercise, viewpoint
    title: str
    description: str
    relevance_score: float
    source: str
    url: Optional[str] = None


class ResourceRecommender:
    """教学资源推荐器"""

    def __init__(self, rag_service=None, wiki_service=None):
        self.rag_service = rag_service
        self.wiki_service = wiki_service

    def recommend(
        self,
        text_analysis: Dict[str, Any],
        student_level: str = "B1",
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, List[ResourceRecommendation]]:
        """
        推荐教学资源

        Args:
            text_analysis: 课文分析结果
            student_level: 学生水平
            focus_areas: 重点领域

        Returns:
            分类的资源推荐
        """
        recommendations = {
            "literature": [],  # 文献推荐
            "courseware": [],  # 课件推荐
            "exercise": [],  # 练习题推荐
            "viewpoint": []  # 对立观点推荐
        }

        # 文献推荐
        recommendations["literature"] = self._recommend_literature(
            text_analysis, student_level
        )

        # 课件推荐
        recommendations["courseware"] = self._recommend_courseware(
            text_analysis, student_level
        )

        # 练习题推荐
        recommendations["exercise"] = self._recommend_exercises(
            text_analysis, student_level
        )

        # 对立观点推荐
        recommendations["viewpoint"] = self._recommend_viewpoints(
            text_analysis
        )

        return recommendations

    def _recommend_literature(
        self,
        text_analysis: Dict[str, Any],
        student_level: str
    ) -> List[ResourceRecommendation]:
        """推荐文献"""
        recommendations = []

        # 基于课文主题推荐
        title = text_analysis.get("title", "")
        if title:
            recommendations.append(ResourceRecommendation(
                resource_type="literature",
                title=f"与《{title}》相关的研究文献",
                description="基于课文主题推荐的相关研究文献",
                relevance_score=0.9,
                source="学术数据库"
            ))

        # 基于体裁推荐
        discourse = text_analysis.get("discourse", {})
        genre = discourse.get("genre_type", "")
        if genre:
            recommendations.append(ResourceRecommendation(
                resource_type="literature",
                title=f"{genre}体裁写作指南",
                description=f"关于{genre}体裁写作方法和技巧的文献",
                relevance_score=0.8,
                source="教学资源库"
            ))

        # 基于词汇推荐
        lexical = text_analysis.get("lexical", {})
        academic_words = lexical.get("academic_words", [])
        if academic_words:
            recommendations.append(ResourceRecommendation(
                resource_type="literature",
                title="学术词汇学习资源",
                description="关于学术词汇学习方法和策略的文献",
                relevance_score=0.7,
                source="Wiki知识库"
            ))

        return recommendations

    def _recommend_courseware(
        self,
        text_analysis: Dict[str, Any],
        student_level: str
    ) -> List[ResourceRecommendation]:
        """推荐课件"""
        recommendations = []

        # 基于语法点推荐
        syntactic = text_analysis.get("syntactic", {})
        sentence_types = syntactic.get("sentence_types", {})

        if sentence_types.get("complex", 0) > 3:
            recommendations.append(ResourceRecommendation(
                resource_type="courseware",
                title="复合句教学课件",
                description="关于复合句结构和用法的教学课件",
                relevance_score=0.85,
                source="教学资源库"
            ))

        # 基于体裁推荐
        discourse = text_analysis.get("discourse", {})
        genre = discourse.get("genre_type", "")
        if genre:
            recommendations.append(ResourceRecommendation(
                resource_type="courseware",
                title=f"{genre}体裁分析课件",
                description=f"关于{genre}体裁结构和特点的教学课件",
                relevance_score=0.8,
                source="Wiki知识库"
            ))

        # 基于认知负荷推荐
        cognitive_load = text_analysis.get("cognitive_load", {})
        if cognitive_load.get("overload", False):
            recommendations.append(ResourceRecommendation(
                resource_type="courseware",
                title="认知负荷管理策略课件",
                description="关于如何管理和降低认知负荷的教学课件",
                relevance_score=0.75,
                source="Wiki知识库"
            ))

        return recommendations

    def _recommend_exercises(
        self,
        text_analysis: Dict[str, Any],
        student_level: str
    ) -> List[ResourceRecommendation]:
        """推荐练习题"""
        recommendations = []

        # 基于词汇推荐
        lexical = text_analysis.get("lexical", {})
        unknown_words = lexical.get("unknown_words", [])

        if unknown_words:
            recommendations.append(ResourceRecommendation(
                resource_type="exercise",
                title="词汇练习题",
                description=f"针对{len(unknown_words)}个生词的词汇练习",
                relevance_score=0.9,
                source="练习题库"
            ))

        # 基于语法推荐
        syntactic = text_analysis.get("syntactic", {})
        if syntactic.get("complexity_score", 0) > 6:
            recommendations.append(ResourceRecommendation(
                resource_type="exercise",
                title="句法分析练习",
                description="针对复杂句结构的分析练习",
                relevance_score=0.85,
                source="练习题库"
            ))

        # 基于体裁推荐
        discourse = text_analysis.get("discourse", {})
        genre = discourse.get("genre_type", "")
        if genre == "argumentative":
            recommendations.append(ResourceRecommendation(
                resource_type="exercise",
                title="论证分析练习",
                description="针对议论文论证结构的分析练习",
                relevance_score=0.8,
                source="练习题库"
            ))

        # 基于阅读理解推荐
        recommendations.append(ResourceRecommendation(
            resource_type="exercise",
            title="阅读理解练习",
            description="针对课文内容的阅读理解练习",
            relevance_score=0.95,
            source="练习题库"
        ))

        return recommendations

    def _recommend_viewpoints(
        self,
        text_analysis: Dict[str, Any]
    ) -> List[ResourceRecommendation]:
        """推荐对立观点"""
        recommendations = []

        # 基于体裁推荐
        discourse = text_analysis.get("discourse", {})
        genre = discourse.get("genre_type", "")

        if genre == "argumentative":
            recommendations.append(ResourceRecommendation(
                resource_type="viewpoint",
                title="对立观点分析",
                description="针对课文论点的对立观点和反驳",
                relevance_score=0.9,
                source="Wiki知识库"
            ))

        # 基于主题推荐
        title = text_analysis.get("title", "")
        if title:
            recommendations.append(ResourceRecommendation(
                resource_type="viewpoint",
                title="多元视角分析",
                description=f"从不同角度分析《{title}》主题",
                relevance_score=0.8,
                source="学术数据库"
            ))

        return recommendations
