"""
数据库模型
"""

from app.models.user import User
from app.models.analysis import AnalysisRecord, LessonPlan
from app.models.learning import LearningRecord, UserFeedback, UserBehavior
from app.models.document import Document, DocumentChunk
from app.models.generation import GenerationLog
from app.models.courseware import (
    CoursewareProject,
    CoursewareVersion,
    PresentationProfile,
    ExportArtifact,
    ComponentDefinition,
)

__all__ = [
    "User",
    "AnalysisRecord",
    "LessonPlan",
    "LearningRecord",
    "UserFeedback",
    "Document",
    "DocumentChunk",
    "UserBehavior",
    "GenerationLog",
    "CoursewareProject",
    "CoursewareVersion",
    "PresentationProfile",
    "ExportArtifact",
    "ComponentDefinition",
]
