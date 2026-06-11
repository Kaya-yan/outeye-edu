"""
智能分析服务模块

提供多维度文本分析功能
"""

from .text_analyzer import TextAnalyzer
from .lexical_analyzer import LexicalAnalyzer
from .syntactic_analyzer import SyntacticAnalyzer
from .discourse_analyzer import DiscourseAnalyzer
from .cognitive_load_analyzer import CognitiveLoadAnalyzer
from .lesson_plan_generator import LessonPlanGenerator
from .resource_recommender import ResourceRecommender
from .learning_analytics import LearningAnalytics

__all__ = [
    "TextAnalyzer",
    "LexicalAnalyzer",
    "SyntacticAnalyzer",
    "DiscourseAnalyzer",
    "CognitiveLoadAnalyzer",
    "LessonPlanGenerator",
    "ResourceRecommender",
    "LearningAnalytics"
]
