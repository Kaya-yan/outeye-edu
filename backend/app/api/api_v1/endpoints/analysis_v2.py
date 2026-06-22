"""
智能分析API端点

提供多维度课文分析和教案生成的API接口
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import uuid
import time

from app.utils.error_handler import handle_api_error
from app.core.database import get_async_db
from app.core.security import get_current_user
from app.models.analysis import AnalysisRecord

router = APIRouter()


# ============ 请求/响应模型 ============

class TextAnalysisRequest(BaseModel):
    """课文分析请求"""
    text: str = Field(..., description="课文内容")
    title: str = Field("", description="课文标题")
    student_level: str = Field("B1", description="学生水平（CEFR）")
    learning_objectives: Optional[List[str]] = Field(None, description="学习目标")


class LessonPlanRequest(BaseModel):
    """教案生成请求"""
    text: str = Field(..., description="课文内容")
    title: str = Field("", description="课文标题")
    student_level: str = Field("B1", description="学生水平")
    lesson_duration: int = Field(45, description="课时（分钟）", ge=30, le=120)
    focus_skills: Optional[List[str]] = Field(None, description="重点技能")


class LexicalAnalysisResponse(BaseModel):
    """词汇分析响应"""
    total_words: int
    unique_words: int
    vocabulary_richness: float
    academic_word_count: int
    academic_words: List[str]
    unknown_words: List[str]
    cefr_distribution: Dict[str, int]
    difficulty_score: float


class SyntacticAnalysisResponse(BaseModel):
    """句法分析响应"""
    total_sentences: int
    total_words: int
    avg_sentence_length: float
    sentence_types: Dict[str, int]
    clause_density: float
    complexity_score: float
    flesch_kincaid_grade: float
    flesch_reading_ease: float


class DiscourseAnalysisResponse(BaseModel):
    """语篇分析响应"""
    coherence_score: float
    genre_type: str
    cohesion_devices: Dict[str, int]
    thematic_progression: str
    paragraph_count: int
    avg_paragraph_length: float
    topic_consistency: float


class CognitiveLoadResponse(BaseModel):
    """认知负荷响应"""
    intrinsic_load: float
    extraneous_load: float
    germane_load: float
    total_load: float
    overload: bool
    recommendations: List[str]


class TextAnalysisResponse(BaseModel):
    """课文分析响应"""
    text_id: str
    title: str
    lexical: LexicalAnalysisResponse
    syntactic: SyntacticAnalysisResponse
    discourse: DiscourseAnalysisResponse
    cognitive_load: CognitiveLoadResponse
    overall_difficulty: float
    cefr_level: str
    teaching_suggestions: List[str]
    analysis_summary: str


class LearningObjectiveResponse(BaseModel):
    """学习目标响应"""
    description: str
    bloom_level: str
    measurable: bool
    assessment_method: str


class TeachingActivityResponse(BaseModel):
    """教学活动响应"""
    name: str
    description: str
    duration: int
    activity_type: str
    materials: List[str]
    interaction_pattern: str


class LessonPlanResponse(BaseModel):
    """教案响应"""
    title: str
    level: str
    duration: int
    objectives: List[LearningObjectiveResponse]
    activities: List[TeachingActivityResponse]
    materials: List[str]
    assessment: Dict[str, Any]
    differentiation: Dict[str, List[str]]
    homework: Optional[str]
    formatted_plan: str


# ============ 服务初始化 ============

_text_analyzer = None
_lesson_plan_generator = None


def get_analysis_services():
    """获取分析服务实例"""
    global _text_analyzer, _lesson_plan_generator

    if _text_analyzer is None:
        from app.services.analysis import TextAnalyzer, LessonPlanGenerator

        _text_analyzer = TextAnalyzer()
        _lesson_plan_generator = LessonPlanGenerator()

    return {
        'analyzer': _text_analyzer,
        'generator': _lesson_plan_generator
    }


# ============ API端点 ============

@router.post("/analyze", response_model=TextAnalysisResponse)
async def analyze_text(
    request: TextAnalysisRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    分析课文

    提供多维度的课文分析，包括词汇、句法、语篇和认知负荷
    """
    try:
        start_time = time.time()
        services = get_analysis_services()
        analyzer = services['analyzer']

        # 执行分析
        result = analyzer.analyze(
            text=request.text,
            title=request.title,
            student_level=request.student_level,
            learning_objectives=request.learning_objectives
        )

        analysis_duration = time.time() - start_time

        # 持久化到数据库
        record = AnalysisRecord(
            id=str(uuid.uuid4()),
            user_id=current_user["user_id"],
            text_title=request.title or "Untitled",
            text_content=request.text,
            text_word_count=result.lexical.total_words,
            student_level=request.student_level,
            lexical_result={
                "total_words": result.lexical.total_words,
                "unique_words": result.lexical.unique_words,
                "vocabulary_richness": result.lexical.vocabulary_richness,
                "academic_word_count": result.lexical.academic_word_count,
                "academic_words": result.lexical.academic_words,
                "unknown_words": result.lexical.unknown_words,
                "cefr_distribution": result.lexical.cefr_distribution,
                "difficulty_score": result.lexical.difficulty_score,
            },
            syntactic_result={
                "total_sentences": result.syntactic.total_sentences,
                "avg_sentence_length": result.syntactic.avg_sentence_length,
                "sentence_types": result.syntactic.sentence_types,
                "clause_density": result.syntactic.clause_density,
                "complexity_score": result.syntactic.complexity_score,
                "flesch_kincaid_grade": result.syntactic.flesch_kincaid_grade,
                "flesch_reading_ease": result.syntactic.flesch_reading_ease,
            },
            discourse_result={
                "coherence_score": result.discourse.coherence_score,
                "genre_type": result.discourse.genre_type,
                "cohesion_devices": result.discourse.cohesion_devices,
                "thematic_progression": result.discourse.thematic_progression,
                "paragraph_count": result.discourse.paragraph_count,
                "topic_consistency": result.discourse.topic_consistency,
            },
            cognitive_load_result={
                "intrinsic_load": result.cognitive_load.intrinsic_load,
                "extraneous_load": result.cognitive_load.extraneous_load,
                "germane_load": result.cognitive_load.germane_load,
                "total_load": result.cognitive_load.total_load,
                "overload": result.cognitive_load.overload,
                "recommendations": result.cognitive_load.recommendations,
            },
            overall_difficulty=result.overall_difficulty,
            cefr_level=result.cefr_level,
            teaching_suggestions=result.teaching_suggestions,
            analysis_duration=analysis_duration,
            model_used="rule-based",
            analysis_status="completed",
        )
        db.add(record)
        await db.commit()

        logger.info(f"Analysis result saved: {record.id}")

        # 转换为响应格式
        return TextAnalysisResponse(
            text_id=result.text_id,
            title=result.title,
            lexical=LexicalAnalysisResponse(
                total_words=result.lexical.total_words,
                unique_words=result.lexical.unique_words,
                vocabulary_richness=result.lexical.vocabulary_richness,
                academic_word_count=result.lexical.academic_word_count,
                academic_words=result.lexical.academic_words,
                unknown_words=result.lexical.unknown_words,
                cefr_distribution=result.lexical.cefr_distribution,
                difficulty_score=result.lexical.difficulty_score
            ),
            syntactic=SyntacticAnalysisResponse(
                total_sentences=result.syntactic.total_sentences,
                total_words=result.syntactic.total_words,
                avg_sentence_length=result.syntactic.avg_sentence_length,
                sentence_types=result.syntactic.sentence_types,
                clause_density=result.syntactic.clause_density,
                complexity_score=result.syntactic.complexity_score,
                flesch_kincaid_grade=result.syntactic.flesch_kincaid_grade,
                flesch_reading_ease=result.syntactic.flesch_reading_ease
            ),
            discourse=DiscourseAnalysisResponse(
                coherence_score=result.discourse.coherence_score,
                genre_type=result.discourse.genre_type,
                cohesion_devices=result.discourse.cohesion_devices,
                thematic_progression=result.discourse.thematic_progression,
                paragraph_count=result.discourse.paragraph_count,
                avg_paragraph_length=result.discourse.avg_paragraph_length,
                topic_consistency=result.discourse.topic_consistency
            ),
            cognitive_load=CognitiveLoadResponse(
                intrinsic_load=result.cognitive_load.intrinsic_load,
                extraneous_load=result.cognitive_load.extraneous_load,
                germane_load=result.cognitive_load.germane_load,
                total_load=result.cognitive_load.total_load,
                overload=result.cognitive_load.overload,
                recommendations=result.cognitive_load.recommendations
            ),
            overall_difficulty=result.overall_difficulty,
            cefr_level=result.cefr_level,
            teaching_suggestions=result.teaching_suggestions,
            analysis_summary=result.analysis_summary
        )

    except Exception as e:
        raise handle_api_error(e, "Analysis")


@router.post("/analyze/detailed", response_model=Dict[str, Any])
async def analyze_text_detailed(
    request: TextAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    详细分析课文

    返回完整的分析报告，包括所有维度的详细数据
    """
    try:
        services = get_analysis_services()
        analyzer = services['analyzer']

        # 执行分析
        result = analyzer.analyze(
            text=request.text,
            title=request.title,
            student_level=request.student_level,
            learning_objectives=request.learning_objectives
        )

        # 生成详细报告
        return analyzer.generate_detailed_report(result)

    except Exception as e:
        raise handle_api_error(e, "Analysis")


@router.post("/generate-lesson-plan", response_model=LessonPlanResponse)
async def generate_lesson_plan(
    request: LessonPlanRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    生成教案

    基于课文分析结果自动生成个性化教案
    """
    try:
        services = get_analysis_services()
        analyzer = services['analyzer']
        generator = services['generator']

        # 先分析课文
        analysis_result = analyzer.analyze(
            text=request.text,
            title=request.title,
            student_level=request.student_level
        )

        # 转换分析结果为字典
        text_analysis = {
            "title": request.title,
            "lexical": {
                "academic_words": analysis_result.lexical.academic_words,
                "unknown_words": analysis_result.lexical.unknown_words
            },
            "discourse": {
                "genre_type": analysis_result.discourse.genre_type
            }
        }

        # 生成教案
        lesson_plan = generator.generate(
            text_analysis=text_analysis,
            student_level=request.student_level,
            lesson_duration=request.lesson_duration,
            focus_skills=request.focus_skills
        )

        # 格式化教案
        formatted_plan = generator.format_lesson_plan(lesson_plan)

        # 持久化教案到数据库
        from app.models.analysis import LessonPlan as LessonPlanModel

        lp_record = LessonPlanModel(
            id=str(uuid.uuid4()),
            user_id=current_user["user_id"],
            title=request.title or "Untitled Lesson Plan",
            student_level=request.student_level,
            duration=request.lesson_duration,
            objectives=[{"description": o.description, "bloom_level": o.bloom_level, "measurable": o.measurable, "assessment_method": o.assessment_method} for o in lesson_plan.objectives],
            activities=[{"name": a.name, "description": a.description, "duration": a.duration, "activity_type": a.activity_type, "materials": a.materials, "interaction_pattern": a.interaction_pattern} for a in lesson_plan.activities],
            materials=lesson_plan.materials,
            assessment=lesson_plan.assessment,
            differentiation=lesson_plan.differentiation,
            homework=lesson_plan.homework,
            formatted_plan=formatted_plan,
        )
        db.add(lp_record)
        await db.commit()

        logger.info(f"Lesson plan saved: {lp_record.id}")

        # 转换为响应格式
        return LessonPlanResponse(
            title=lesson_plan.title,
            level=lesson_plan.level,
            duration=lesson_plan.duration,
            objectives=[
                LearningObjectiveResponse(
                    description=obj.description,
                    bloom_level=obj.bloom_level,
                    measurable=obj.measurable,
                    assessment_method=obj.assessment_method
                )
                for obj in lesson_plan.objectives
            ],
            activities=[
                TeachingActivityResponse(
                    name=act.name,
                    description=act.description,
                    duration=act.duration,
                    activity_type=act.activity_type,
                    materials=act.materials,
                    interaction_pattern=act.interaction_pattern
                )
                for act in lesson_plan.activities
            ],
            materials=lesson_plan.materials,
            assessment=lesson_plan.assessment,
            differentiation=lesson_plan.differentiation,
            homework=lesson_plan.homework,
            formatted_plan=formatted_plan
        )

    except Exception as e:
        raise handle_api_error(e, "Analysis")


@router.post("/analyze/lexical", response_model=LexicalAnalysisResponse)
async def analyze_lexical(
    request: TextAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    词汇分析

    分析课文的词汇特征
    """
    try:
        from app.services.analysis import LexicalAnalyzer

        analyzer = LexicalAnalyzer()
        result = analyzer.analyze(request.text, request.student_level)

        return LexicalAnalysisResponse(
            total_words=result.total_words,
            unique_words=result.unique_words,
            vocabulary_richness=result.vocabulary_richness,
            academic_word_count=result.academic_word_count,
            academic_words=result.academic_words,
            unknown_words=result.unknown_words,
            cefr_distribution=result.cefr_distribution,
            difficulty_score=result.difficulty_score
        )

    except Exception as e:
        raise handle_api_error(e, "Analysis")


@router.post("/analyze/syntactic", response_model=SyntacticAnalysisResponse)
async def analyze_syntactic(
    request: TextAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    句法分析

    分析课文的句法特征
    """
    try:
        from app.services.analysis import SyntacticAnalyzer

        analyzer = SyntacticAnalyzer()
        result = analyzer.analyze(request.text)

        return SyntacticAnalysisResponse(
            total_sentences=result.total_sentences,
            total_words=result.total_words,
            avg_sentence_length=result.avg_sentence_length,
            sentence_types=result.sentence_types,
            clause_density=result.clause_density,
            complexity_score=result.complexity_score,
            flesch_kincaid_grade=result.flesch_kincaid_grade,
            flesch_reading_ease=result.flesch_reading_ease
        )

    except Exception as e:
        raise handle_api_error(e, "Analysis")


@router.post("/analyze/discourse", response_model=DiscourseAnalysisResponse)
async def analyze_discourse(
    request: TextAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    语篇分析

    分析课文的语篇特征
    """
    try:
        from app.services.analysis import DiscourseAnalyzer

        analyzer = DiscourseAnalyzer()
        result = analyzer.analyze(request.text)

        return DiscourseAnalysisResponse(
            coherence_score=result.coherence_score,
            genre_type=result.genre_type,
            cohesion_devices=result.cohesion_devices,
            thematic_progression=result.thematic_progression,
            paragraph_count=result.paragraph_count,
            avg_paragraph_length=result.avg_paragraph_length,
            topic_consistency=result.topic_consistency
        )

    except Exception as e:
        raise handle_api_error(e, "Analysis")


@router.post("/analyze/cognitive-load", response_model=CognitiveLoadResponse)
async def analyze_cognitive_load(
    request: TextAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    认知负荷分析

    分析课文的认知负荷
    """
    try:
        from app.services.analysis import CognitiveLoadAnalyzer

        analyzer = CognitiveLoadAnalyzer()
        result = analyzer.analyze(request.text, request.student_level)

        return CognitiveLoadResponse(
            intrinsic_load=result.intrinsic_load,
            extraneous_load=result.extraneous_load,
            germane_load=result.germane_load,
            total_load=result.total_load,
            overload=result.overload,
            recommendations=result.recommendations
        )

    except Exception as e:
        raise handle_api_error(e, "Analysis")
