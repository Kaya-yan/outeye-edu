"""
白盒分析API端点

提供透明、可验证的课文分析，输出教师能看懂的指标。
如果白盒分析失败，优雅回退到旧分析引擎。
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
import asyncio
import json
import uuid
import time
from datetime import datetime
from urllib.parse import quote

from app.utils.error_handler import handle_api_error
from app.core.database import AsyncSessionLocal, get_async_db
from app.core.security import get_current_user
from app.models.analysis import AnalysisRecord, LessonPlanVersion, AnalysisProgress, AnalysisIntent
from app.models.courseware import TeacherStyleEvent
from app.services.teacher_intent import sanitize_intent

router = APIRouter()


# ============ 请求/响应模型 ============

class WhiteboxAnalysisRequest(BaseModel):
    """白盒分析请求"""
    text: str = Field(..., description="课文内容", min_length=20)
    title: str = Field("", description="课文标题")
    student_level: str = Field("B1", description="学生水平（CEFR）", pattern=r"^(A1|A2|B1|B2|C1|C2)$")
    language: Optional[str] = Field(None, description="指定语言代码（en/ja/fr/de/es/ko），为空则自动检测", pattern=r"^[a-z]{2}$")
    native_language: Optional[str] = Field(None, description="学生母语代码（如zh/ja/ko等）", pattern=r"^[a-z]{2}$")
    course_type: Optional[str] = Field(None, description="课程类型：精读/泛读/听说/写作/综合")
    class_size: Optional[int] = Field(None, description="班级人数", ge=1, le=200)
    duration_minutes: Optional[int] = Field(None, description="课时时长（分钟）", ge=5, le=180)


class DifficultWordResponse(BaseModel):
    """超纲词响应"""
    word: str
    level: str
    count: int
    in_awl: bool


class VocabResponse(BaseModel):
    """词汇分析响应"""
    total_words: int
    unique_words: int
    cefr_distribution: Dict[str, int]
    awl_count: int
    awl_ratio: float
    difficult_words: List[DifficultWordResponse]
    vocabulary_richness: float


class LongestSentenceResponse(BaseModel):
    """最长句响应"""
    preview: str
    word_count: int
    index: int


class SyntaxResponse(BaseModel):
    """句法分析响应"""
    total_sentences: int
    avg_sentence_length: float
    max_sentence: LongestSentenceResponse
    long_sentences_count: int
    very_long_sentences_count: int
    flesch_reading_ease: float


class ParagraphFunctionResponse(BaseModel):
    """段落功能响应"""
    index: int
    function: str
    preview: str


class DiscourseResponse(BaseModel):
    """语篇分析响应"""
    paragraph_count: int
    connective_density: float
    paragraph_functions: List[ParagraphFunctionResponse]
    genre_hint: str


class LearnerGapResponse(BaseModel):
    """学习者适配响应"""
    text_level: str
    student_level: str
    gap: str
    gap_description: str


class WhiteboxAnalysisResponse(BaseModel):
    """白盒分析完整响应"""
    text_id: str
    title: str
    text_level: str
    language: str = "en"
    language_name: str = "英语"
    vocabulary: VocabResponse
    syntax: SyntaxResponse
    discourse: DiscourseResponse
    learner_gap: LearnerGapResponse
    enhancement_tags: List[str]
    teaching_tips: List[str]
    analysis_version: str
    analysis_duration: float
    fallback_used: bool = False


class FallbackAnalysisResponse(BaseModel):
    """旧引擎回退响应"""
    text_id: str
    title: str
    overall_difficulty: float
    cefr_level: str
    analysis_summary: str
    teaching_suggestions: List[str]
    fallback_used: bool = True
    fallback_reason: str


# ============ API端点 ============

@router.post("/whitebox", response_model=Dict[str, Any])
async def whitebox_analyze(
    request: WhiteboxAnalysisRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
):
    """
    白盒分析端点

    返回透明、可验证的分析指标。
    如果白盒分析失败，优雅回退到旧分析引擎。
    """
    start_time = time.time()

    try:
        # 尝试白盒分析
        from app.services.analysis.whitebox_analyzer import WhiteboxAnalyzer
        from app.services.analysis.tag_generator import generate_tag_details, get_wiki_tags_for_retrieval, get_rag_tags_for_retrieval

        analyzer = WhiteboxAnalyzer()
        result = analyzer.analyze(request.text, request.student_level, language=request.language)

        # F4.3：残差低频词 LLM 兜底分级（word_level_cache 缓存优先；失败原样保留未分级）
        vocab_grading = None
        if result.language == "en":
            unknown_words = [w.word for w in result.vocabulary.difficult_words if w.level == "unknown"]
            if unknown_words:
                try:
                    from app.services.analysis.word_grader import grade_ungraded_words, merge_levels_into_result

                    levels, gmeta = await grade_ungraded_words(unknown_words, lang="en")
                    merged_n = merge_levels_into_result(result, levels)
                    vocab_grading = {**gmeta, "merged": merged_n}
                except Exception as e:
                    logger.warning(f"LLM 兜底分级异常，跳过: {type(e).__name__}: {e}")
                    vocab_grading = {"fallback": True}

        # 生成标签详情
        tag_details = generate_tag_details(result)
        wiki_tags = get_wiki_tags_for_retrieval(tag_details)
        rag_tags = get_rag_tags_for_retrieval(tag_details)

        duration = time.time() - start_time

        # 保存到数据库
        record_id = str(uuid.uuid4())
        record = AnalysisRecord(
            id=record_id,
            user_id=current_user["user_id"],
            text_title=request.title or "Untitled",
            text_content=request.text,
            text_word_count=result.vocabulary.total_words,
            student_level=request.student_level,
            course_type=request.course_type,
            duration_minutes=request.duration_minutes,
            analysis_status="completed",
            lexical_result={
                "total_words": result.vocabulary.total_words,
                "unique_words": result.vocabulary.unique_words,
                "cefr_distribution": result.vocabulary.cefr_distribution,
                "awl_count": result.vocabulary.awl_count,
                "awl_ratio": result.vocabulary.awl_ratio,
                "difficult_words": [
                    {"word": d.word, "level": d.level, "count": d.count, "in_awl": d.in_awl}
                    for d in result.vocabulary.difficult_words
                ],
                "vocabulary_richness": result.vocabulary.vocabulary_richness,
            },
            syntactic_result={
                "total_sentences": result.syntax.total_sentences,
                "avg_sentence_length": result.syntax.avg_sentence_length,
                "max_sentence": {
                    "preview": result.syntax.max_sentence.preview,
                    "word_count": result.syntax.max_sentence.word_count,
                    "index": result.syntax.max_sentence.index,
                },
                "long_sentences_count": result.syntax.long_sentences_count,
                "very_long_sentences_count": result.syntax.very_long_sentences_count,
                "flesch_reading_ease": result.syntax.flesch_reading_ease,
            },
            discourse_result={
                "paragraph_count": result.discourse.paragraph_count,
                "connective_density": result.discourse.connective_density,
                "paragraph_functions": [
                    {"index": p.index, "function": p.function, "preview": p.preview}
                    for p in result.discourse.paragraph_functions
                ],
                "genre_hint": result.discourse.genre_hint,
            },
            overall_difficulty=0.0,  # 白盒分析不输出黑盒分数
            cefr_level=result.text_level,
            teaching_suggestions=result.teaching_tips,
            analysis_duration=duration,
            model_used="whitebox-v1",
            enhancement_tags=result.enhancement_tags,
            learner_gap={
                "text_level": result.learner_gap.text_level,
                "student_level": result.learner_gap.student_level,
                "gap": result.learner_gap.gap,
                "gap_description": result.learner_gap.gap_description,
            },
        )
        db.add(record)
        await db.commit()

        # 构建响应
        response = {
            "text_id": record_id,
            "title": request.title or "Untitled",
            "text_level": result.text_level,
            "language": result.language,
            "language_name": result.language_name,
            "vocabulary": {
                "total_words": result.vocabulary.total_words,
                "unique_words": result.vocabulary.unique_words,
                "cefr_distribution": result.vocabulary.cefr_distribution,
                "awl_count": result.vocabulary.awl_count,
                "awl_ratio": result.vocabulary.awl_ratio,
                "difficult_words": [
                    {"word": d.word, "level": d.level, "count": d.count, "in_awl": d.in_awl}
                    for d in result.vocabulary.difficult_words
                ],
                "vocabulary_richness": result.vocabulary.vocabulary_richness,
            },
            "syntax": {
                "total_sentences": result.syntax.total_sentences,
                "avg_sentence_length": result.syntax.avg_sentence_length,
                "max_sentence": {
                    "preview": result.syntax.max_sentence.preview,
                    "word_count": result.syntax.max_sentence.word_count,
                    "index": result.syntax.max_sentence.index,
                },
                "long_sentences_count": result.syntax.long_sentences_count,
                "very_long_sentences_count": result.syntax.very_long_sentences_count,
                "flesch_reading_ease": result.syntax.flesch_reading_ease,
            },
            "discourse": {
                "paragraph_count": result.discourse.paragraph_count,
                "connective_density": result.discourse.connective_density,
                "paragraph_functions": [
                    {"index": p.index, "function": p.function, "preview": p.preview}
                    for p in result.discourse.paragraph_functions
                ],
                "genre_hint": result.discourse.genre_hint,
                "text_structure": result.discourse.text_structure,
                "teaching_points": result.discourse.teaching_points,
            },
            "learner_gap": {
                "text_level": result.learner_gap.text_level,
                "student_level": result.learner_gap.student_level,
                "gap": result.learner_gap.gap,
                "gap_description": result.learner_gap.gap_description,
            },
            "enhancement_tags": result.enhancement_tags,
            "tag_labels": result.tag_labels,
            "teaching_insights": result.teaching_insights,
            "cultural_elements": [
                {"category": e.category, "keyword": e.keyword, "context": e.context, "explanation": e.explanation}
                for e in result.cultural_elements
            ],
            "tag_details": tag_details,
            "wiki_tags": wiki_tags,
            "rag_tags": rag_tags,
            "teaching_tips": result.teaching_tips,
            "analysis_version": result.analysis_version,
            "analysis_duration": round(duration, 2),
            "fallback_used": False,
            "vocab_grading": vocab_grading,
        }

        logger.info(f"白盒分析完成: {record_id}, 耗时{duration:.2f}s, 标签{len(result.enhancement_tags)}个")
        return response

    except Exception as e:
        # 白盒分析失败，回退到旧引擎
        logger.warning(f"白盒分析失败，回退到旧引擎: {e}")
        return await _fallback_analyze(request, db, current_user, str(e))


async def _fallback_analyze(
    request: WhiteboxAnalysisRequest,
    db: AsyncSession,
    current_user: dict,
    reason: str,
) -> Dict[str, Any]:
    """回退到旧分析引擎"""
    try:
        from app.services.analysis.text_analyzer import TextAnalyzer

        analyzer = TextAnalyzer()
        result = analyzer.analyze(request.text, request.title, request.student_level)

        record_id = str(uuid.uuid4())
        duration = 0.0

        # 保存到数据库
        record = AnalysisRecord(
            id=record_id,
            user_id=current_user["user_id"],
            text_title=request.title or "Untitled",
            text_content=request.text,
            text_word_count=result.lexical.total_words,
            student_level=request.student_level,
            analysis_status="completed",
            lexical_result={
                "total_words": result.lexical.total_words,
                "unique_words": result.lexical.unique_words,
                "cefr_distribution": result.lexical.cefr_distribution,
                "academic_word_count": result.lexical.academic_word_count,
                "difficulty_score": result.lexical.difficulty_score,
            },
            syntactic_result={
                "total_sentences": result.syntactic.total_sentences,
                "avg_sentence_length": result.syntactic.avg_sentence_length,
                "complexity_score": result.syntactic.complexity_score,
            },
            discourse_result={
                "coherence_score": result.discourse.coherence_score,
                "genre_type": result.discourse.genre_type,
            },
            cognitive_load_result={
                "total_load": result.cognitive_load.total_load,
                "overload": result.cognitive_load.overload,
            },
            overall_difficulty=result.overall_difficulty,
            cefr_level=result.cefr_level,
            teaching_suggestions=result.teaching_suggestions,
            analysis_duration=duration,
            model_used="rule-based-fallback",
        )
        db.add(record)
        await db.commit()

        return {
            "text_id": record_id,
            "title": request.title or "Untitled",
            "overall_difficulty": result.overall_difficulty,
            "cefr_level": result.cefr_level,
            "analysis_summary": result.analysis_summary,
            "teaching_suggestions": result.teaching_suggestions,
            "analysis_duration": round(duration, 2),
            "fallback_used": True,
            "fallback_reason": "白盒分析引擎暂时不可用，已使用备用引擎",
        }

    except Exception as fallback_error:
        logger.error(f"旧引擎也失败: {fallback_error}")
        raise HTTPException(
            status_code=500,
            detail="分析引擎暂时不可用，请稍后重试"
        )


# ============ 文化背景具体化端点 ============

class CultureEnrichRequest(BaseModel):
    """文化背景具体化请求"""
    text: str = Field(..., description="课文内容", min_length=20)
    language_name: str = Field("英语", description="语言显示名称")
    cultural_elements: List[Dict[str, Any]] = Field(
        ..., description="白盒分析检测到的文化元素 [{category, keyword, context, explanation}]", min_length=1
    )


@router.post("/culture-enrich", response_model=Dict[str, Any])
async def culture_enrich(
    request: CultureEnrichRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    文化背景 LLM 具体化端点

    白盒检测保持确定性；本端点用 LLM 把模板化"教学建议"替换为
    具体事实性背景（起源/年代/地点/当代形态）。失败时返回原始
    元素并 fallback=True，由前端标注。
    """
    from app.services.analysis.culture_enricher import enrich_cultural_elements

    try:
        result = await asyncio.to_thread(
            enrich_cultural_elements,
            text=request.text,
            language_name=request.language_name,
            elements=request.cultural_elements,
        )
        return {
            "cultural_elements": result.items,
            "prompt_version": result.prompt_version,
            "model": result.model,
            "fallback": result.fallback,
            "self_check": result.self_check,
            "generation_duration": result.generation_duration,
        }
    except Exception as e:
        logger.error(f"文化背景具体化失败: {e}")
        return {
            "cultural_elements": request.cultural_elements,
            "prompt_version": "",
            "model": "template-fallback",
            "fallback": True,
            "self_check": {"error": str(e)},
            "generation_duration": 0,
        }


# ============ 双源检索端点 ============

class RetrieveRequest(BaseModel):
    """双源检索请求"""
    wiki_tags: List[str] = Field(..., description="Wiki检索标签", min_length=1)
    rag_tags: List[str] = Field(..., description="RAG检索标签", min_length=1)
    enhancement_tags: List[str] = Field(default=[], description="增强标签")
    text_title: str = Field("", description="课文标题")
    max_results: int = Field(5, description="每源最大结果数", ge=1, le=10)


@router.post("/retrieve", response_model=Dict[str, Any])
async def dual_retrieve(
    request: RetrieveRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    双源并行检索端点

    基于白盒分析的增强标签，并行从 Wiki（教学理论）和 RAG（教学资源）检索。
    """
    try:
        from app.services.analysis.dual_retriever import DualRetriever

        retriever = DualRetriever()
        result = retriever.retrieve(
            wiki_tags=request.wiki_tags,
            rag_tags=request.rag_tags,
            enhancement_tags=request.enhancement_tags,
            text_title=request.text_title,
            max_wiki_results=request.max_results,
            max_rag_results=request.max_results,
        )

        response = {
            "wiki_results": [
                {
                    "page_name": r.page_name,
                    "title": r.title,
                    "summary": r.summary,
                    "relevance_score": r.relevance_score,
                    "match_type": r.match_type,
                    "tags": r.tags,
                    "matched_sections": r.matched_sections,
                }
                for r in result.wiki_results
            ],
            "rag_results": [
                {
                    "chunk_id": r.chunk_id,
                    "content": r.content,
                    "score": r.score,
                    "doc_id": r.doc_id,
                    "metadata": r.metadata,
                }
                for r in result.rag_results
            ],
            "wiki_query_used": result.wiki_query_used,
            "rag_query_used": result.rag_query_used,
            "retrieval_duration": result.retrieval_duration,
            "wiki_count": result.wiki_count,
            "rag_count": result.rag_count,
        }

        logger.info(f"双源检索完成: Wiki={result.wiki_count}条, RAG={result.rag_count}条, 耗时{result.retrieval_duration}s")
        return response

    except Exception as e:
        logger.error(f"双源检索失败: {e}")
        raise HTTPException(status_code=500, detail="检索失败，请稍后重试")


# ============ 融合生成端点 ============

class GeneratePlanRequest(BaseModel):
    """融合生成请求"""
    text: str = Field(..., description="课文内容", min_length=20)
    title: str = Field("", description="课文标题")
    student_level: str = Field("B1", description="学生水平（CEFR）", pattern=r"^(A1|A2|B1|B2|C1|C2)$")
    language: Optional[str] = Field(None, description="指定语言代码", pattern=r"^[a-z]{2}$")
    native_language: Optional[str] = Field(None, description="学生母语代码", pattern=r"^[a-z]{2}$")
    course_type: Optional[str] = Field(None, description="课程类型：精读/泛读/听说/写作/综合")
    class_size: Optional[int] = Field(None, description="班级人数", ge=1, le=200)
    duration_minutes: int = Field(90, description="课时时长（分钟）", ge=5, le=180)
    mode: str = Field("enhanced", description="生成模式：basic/enhanced", pattern=r"^(basic|enhanced)$")
    max_retrieval_results: int = Field(3, description="每源最大检索数", ge=1, le=10)
    analysis_id: Optional[str] = Field(None, description="对应白盒分析记录 id，用于教案版本落库与断点恢复（缺省不落库）")
    teaching_intent: Optional[str] = Field(None, description="教师自定义教学意图（可选，进入提示词前截断+防注入包裹）", max_length=2000)


# ============ 教案版本与进度（③ 历史恢复） ============

_STEP_ORDER = {"analysis": 1, "plan": 2, "confirmed": 3}


async def _upsert_plan_version(db: AsyncSession, analysis_id: str, user_id: str, mode: str, result: Dict[str, Any]) -> str:
    """按 (analysis_id, mode) upsert 教案版本快照，返回版本 id（幂等：重复调用覆盖同一行）"""
    existing = (await db.execute(
        select(LessonPlanVersion).where(
            LessonPlanVersion.analysis_id == analysis_id,
            LessonPlanVersion.mode == mode,
        )
    )).scalar_one_or_none()
    payload = json.dumps(result, ensure_ascii=False)
    if existing is None:
        version = LessonPlanVersion(analysis_id=analysis_id, user_id=user_id, mode=mode, result_json=payload)
        db.add(version)
        await db.flush()
        return version.id
    existing.result_json = payload
    existing.updated_at = datetime.utcnow()
    return existing.id


async def _advance_progress(
    db: AsyncSession,
    analysis_id: str,
    user_id: str,
    step: str,
    confirmed_plan_id: Optional[str] = None,
) -> None:
    """进度只前进不回退（confirmed 后再生成 basic/enhanced 不降级）"""
    progress = (await db.execute(
        select(AnalysisProgress).where(AnalysisProgress.analysis_id == analysis_id)
    )).scalar_one_or_none()
    if progress is None:
        db.add(AnalysisProgress(
            analysis_id=analysis_id,
            user_id=user_id,
            furthest_step=step,
            confirmed_plan_id=confirmed_plan_id,
        ))
    else:
        if _STEP_ORDER.get(step, 0) > _STEP_ORDER.get(progress.furthest_step, 0):
            progress.furthest_step = step
        if confirmed_plan_id:
            progress.confirmed_plan_id = confirmed_plan_id
        progress.updated_at = datetime.utcnow()


async def _persist_plan_version(
    db: AsyncSession,
    analysis_id: Optional[str],
    user_id: str,
    mode: str,
    result: Dict[str, Any],
    teaching_intent: Optional[str] = None,
) -> None:
    """生成结果落库，意图随版本一并 upsert（best-effort：所有权不符或失败仅告警，绝不影响生成返回）"""
    if not analysis_id:
        return
    try:
        record = (await db.execute(
            select(AnalysisRecord.user_id).where(AnalysisRecord.id == analysis_id)
        )).first()
        if record is None or record.user_id != user_id:
            logger.warning(f"教案版本落库跳过：分析记录不存在或非本人 ({analysis_id})")
            return
        await _upsert_plan_version(db, analysis_id, user_id, mode, result)
        await _advance_progress(db, analysis_id, user_id, "plan")
        await _upsert_intent(db, analysis_id, user_id, teaching_intent)
        await db.commit()
    except Exception as e:
        logger.warning(f"教案版本落库失败（不影响返回）: {e}")
        await db.rollback()


async def _upsert_intent(
    db: AsyncSession,
    analysis_id: str,
    user_id: str,
    teaching_intent: Optional[str],
) -> None:
    """意图随分析记录持久化（唯一行 upsert）；非空时同步记一条 intent 风格事件供画像取历史"""
    cleaned = sanitize_intent(teaching_intent or "")
    row = (await db.execute(
        select(AnalysisIntent).where(AnalysisIntent.analysis_id == analysis_id)
    )).scalar_one_or_none()
    if row is None:
        if not cleaned:
            return
        db.add(AnalysisIntent(
            id=str(uuid.uuid4()),
            analysis_id=analysis_id,
            user_id=user_id,
            intent_text=cleaned,
        ))
    else:
        row.intent_text = cleaned
        row.updated_at = datetime.utcnow()
    if cleaned:
        db.add(TeacherStyleEvent(
            id=str(uuid.uuid4()),
            user_id=user_id,
            analysis_id=analysis_id,
            event_type="intent",
            theme=None,
            extra_json={"intent": cleaned[:200]},
        ))


class PlanConfirmRequest(BaseModel):
    """教案确认请求"""
    mode: str = Field(..., description="确认时激活的版本：basic/enhanced", pattern=r"^(basic|enhanced)$")
    result: Dict[str, Any] = Field(..., description="确认的教案生成结果快照")


@router.post("/{analysis_id}/plan-confirm", response_model=Dict[str, Any])
async def confirm_lesson_plan(
    analysis_id: str,
    request: PlanConfirmRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """确认教案：落 confirmed 快照并把进度推进到 confirmed（幂等，重复确认覆盖同一行）"""
    record = (await db.execute(
        select(AnalysisRecord.user_id).where(AnalysisRecord.id == analysis_id)
    )).first()
    if record is None or record.user_id != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析记录不存在")

    snapshot = {"origin_mode": request.mode, "result": request.result}
    version_id = await _upsert_plan_version(db, analysis_id, current_user["user_id"], "confirmed", snapshot)
    await _advance_progress(db, analysis_id, current_user["user_id"], "confirmed", confirmed_plan_id=version_id)
    await db.commit()
    logger.info(f"教案已确认: analysis={analysis_id}, origin={request.mode}")
    return {"analysis_id": analysis_id, "status": "confirmed", "mode": request.mode}


@router.get("/{analysis_id}/resume-state", response_model=Dict[str, Any])
async def get_resume_state(
    analysis_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """恢复状态：furthest_step（无进度行时按 analysis_status 推导）+ 三类版本快照；解析失败的版本跳过不报错"""
    record = (await db.execute(
        select(AnalysisRecord).where(AnalysisRecord.id == analysis_id)
    )).scalar_one_or_none()
    if record is None or record.user_id != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析记录不存在")

    progress = (await db.execute(
        select(AnalysisProgress).where(AnalysisProgress.analysis_id == analysis_id)
    )).scalar_one_or_none()
    if progress is not None:
        furthest = progress.furthest_step
    else:
        furthest = "analysis" if record.analysis_status == "completed" else "input"

    versions: Dict[str, Any] = {"basic": None, "enhanced": None}
    confirmed = None
    rows = (await db.execute(
        select(LessonPlanVersion).where(LessonPlanVersion.analysis_id == analysis_id)
    )).scalars().all()
    for row in rows:
        try:
            parsed = json.loads(row.result_json)
        except (ValueError, TypeError):
            logger.warning(f"教案版本 JSON 解析失败，跳过: {row.id}")
            continue
        if row.mode in versions:
            versions[row.mode] = parsed
        elif row.mode == "confirmed":
            confirmed = parsed

    intent_row = (await db.execute(
        select(AnalysisIntent).where(AnalysisIntent.analysis_id == analysis_id)
    )).scalar_one_or_none()

    return {
        "analysis_id": analysis_id,
        "furthest_step": furthest,
        "versions": versions,
        "confirmed": confirmed,
        "intent": intent_row.intent_text if intent_row else "",
    }


@router.post("/generate-plan", response_model=Dict[str, Any])
async def generate_teaching_plan(
    request: GeneratePlanRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    融合生成端点（完整流水线）

    白盒分析 → 双源检索 → LLM生成教学方案
    """
    start_time = time.time()

    try:
        # Step 1: 白盒分析
        from app.services.analysis.whitebox_analyzer import WhiteboxAnalyzer
        from app.services.analysis.tag_generator import generate_tag_details, get_wiki_tags_for_retrieval, get_rag_tags_for_retrieval

        analyzer = WhiteboxAnalyzer()
        analysis_result = analyzer.analyze(request.text, request.student_level, language=request.language)

        tag_details = generate_tag_details(analysis_result)
        wiki_tags = get_wiki_tags_for_retrieval(tag_details)
        rag_tags = get_rag_tags_for_retrieval(tag_details)

        analysis_dict = {
            "text_level": analysis_result.text_level,
            "language": analysis_result.language,
            "language_name": analysis_result.language_name,
            "vocabulary": {
                "total_words": analysis_result.vocabulary.total_words,
                "unique_words": analysis_result.vocabulary.unique_words,
                "cefr_distribution": analysis_result.vocabulary.cefr_distribution,
                "awl_count": analysis_result.vocabulary.awl_count,
                "awl_ratio": analysis_result.vocabulary.awl_ratio,
                "difficult_words": [
                    {"word": d.word, "level": d.level, "count": d.count, "in_awl": d.in_awl}
                    for d in analysis_result.vocabulary.difficult_words
                ],
                "vocabulary_richness": analysis_result.vocabulary.vocabulary_richness,
            },
            "syntax": {
                "total_sentences": analysis_result.syntax.total_sentences,
                "avg_sentence_length": analysis_result.syntax.avg_sentence_length,
                "max_sentence": {
                    "preview": analysis_result.syntax.max_sentence.preview,
                    "word_count": analysis_result.syntax.max_sentence.word_count,
                    "index": analysis_result.syntax.max_sentence.index,
                },
                "long_sentences_count": analysis_result.syntax.long_sentences_count,
                "very_long_sentences_count": analysis_result.syntax.very_long_sentences_count,
                "flesch_reading_ease": analysis_result.syntax.flesch_reading_ease,
            },
            "discourse": {
                "paragraph_count": analysis_result.discourse.paragraph_count,
                "connective_density": analysis_result.discourse.connective_density,
                "genre_hint": analysis_result.discourse.genre_hint,
                "text_structure": analysis_result.discourse.text_structure,
                "teaching_points": analysis_result.discourse.teaching_points,
            },
            "learner_gap": {
                "text_level": analysis_result.learner_gap.text_level,
                "student_level": analysis_result.learner_gap.student_level,
                "gap": analysis_result.learner_gap.gap,
                "gap_description": analysis_result.learner_gap.gap_description,
            },
            "enhancement_tags": analysis_result.enhancement_tags,
            "tag_labels": analysis_result.tag_labels,
            "teaching_insights": analysis_result.teaching_insights,
            "cultural_elements": [
                {"category": e.category, "keyword": e.keyword, "context": e.context, "explanation": e.explanation}
                for e in analysis_result.cultural_elements
            ],
            "teaching_tips": analysis_result.teaching_tips,
            "student_profile": {
                "native_language": request.native_language,
                "course_type": request.course_type,
                "class_size": request.class_size,
            },
        }

        logger.info(f"白盒分析完成: {analysis_result.text_level}, 标签{len(analysis_result.enhancement_tags)}个")

        # Step 2: 双源检索
        from app.services.analysis.dual_retriever import DualRetriever

        retriever = DualRetriever()
        retrieval_result = retriever.retrieve(
            wiki_tags=wiki_tags,
            rag_tags=rag_tags,
            enhancement_tags=analysis_result.enhancement_tags,
            text_title=request.title,
            max_wiki_results=request.max_retrieval_results,
            max_rag_results=request.max_retrieval_results,
        )

        wiki_results = [
            {
                "title": r.title,
                "summary": r.summary,
                "relevance_score": r.relevance_score,
                "tags": r.tags,
                "confidence": r.confidence,
                "contested": r.contested,
                "contradictions": r.contradictions,
                "sources": r.sources,
                "updated": r.updated,
            }
            for r in retrieval_result.wiki_results
        ]
        rag_results = [
            {
                "content": r.content,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in retrieval_result.rag_results
        ]

        logger.info(f"双源检索完成: Wiki={retrieval_result.wiki_count}, RAG={retrieval_result.rag_count}")

        # Step 3: 融合生成
        from app.services.analysis.fusion_generator import generate_teaching_plan

        plan = generate_teaching_plan(
            text_title=request.title or "Untitled",
            text_content=request.text,
            analysis=analysis_dict,
            wiki_results=wiki_results,
            rag_results=rag_results,
            mode=request.mode,
            duration_minutes=request.duration_minutes,
            course_type=request.course_type,
            class_size=request.class_size,
            native_language=request.native_language,
            teaching_intent=request.teaching_intent,
        )

        # 教学蓝图（仅增强模式单独展示）
        if request.mode == "enhanced":
            from app.services.analysis.blueprint import build_teaching_blueprint
            blueprint = build_teaching_blueprint(
                analysis_dict,
                {"activity_designs": plan.activity_designs},
                wiki_results,
                rag_results,
                request.duration_minutes,
            )
            evidence_annotations = plan.evidence_annotations
        else:
            blueprint = None
            evidence_annotations = None

        total_duration = time.time() - start_time

        response = {
            "text_title": request.title or "Untitled",
            "text_level": analysis_result.text_level,
            "language_name": analysis_result.language_name,
            "student_level": request.student_level,
            "learner_gap": analysis_dict["learner_gap"],
            "vocabulary": analysis_dict["vocabulary"],
            "cultural_elements": analysis_dict["cultural_elements"],
            "enhancement_tags": analysis_result.enhancement_tags,
            "tag_labels": analysis_result.tag_labels,
            "teaching_blueprint": blueprint,
            "teaching_plan": {
                "framework": plan.framework,
                "objectives": plan.objectives,
                "difficulty_overview": plan.difficulty_overview,
                "teaching_suggestions": plan.teaching_suggestions,
                "activity_designs": plan.activity_designs,
                "assessment": plan.assessment,
                "differentiation": plan.differentiation,
                "theoretical_basis": plan.theoretical_basis,
                "self_check": plan.self_check,
            },
            "evidence_annotations": evidence_annotations,
            "sources": plan.sources,
            "retrieval_info": {
                "wiki_count": retrieval_result.wiki_count,
                "rag_count": retrieval_result.rag_count,
                "retrieval_duration": retrieval_result.retrieval_duration,
            },
            "syntax": analysis_dict["syntax"],
            "discourse": analysis_dict["discourse"],
            "generation_settings": {
                "duration_minutes": request.duration_minutes,
                "course_type": request.course_type,
                "class_size": request.class_size,
                "native_language": request.native_language,
            },
            "generation_duration": plan.generation_duration,
            "total_duration": round(total_duration, 2),
            "model": plan.model,
            "prompt_version": plan.prompt_version,
            "fallback": plan.fallback,
        }

        # 生成记录落库：self_check 随产物保存，质量可追溯
        try:
            from app.models.generation import GenerationLog

            db.add(GenerationLog(
                id=str(uuid.uuid4()),
                user_id=current_user["user_id"],
                analysis_id=None,
                stage="lesson_plan",
                prompt_name="lesson_plan_v2",
                prompt_version=plan.prompt_version,
                model=plan.model,
                fallback="yes" if plan.fallback else "no",
                generation_duration=plan.generation_duration,
                self_check=plan.self_check or None,
            ))
            await db.commit()
        except Exception as log_err:
            logger.warning(f"生成记录落库失败（不影响返回）: {log_err}")

        # 教案版本落库（③ 历史恢复）：携带 analysis_id 时持久化，失败不影响返回
        await _persist_plan_version(db, request.analysis_id, current_user["user_id"], request.mode, response, teaching_intent=request.teaching_intent)

        logger.info(f"教学方案生成完成: 总耗时{total_duration:.2f}s")
        return response

    except Exception as e:
        logger.error(f"教学方案生成失败: {e}")
        raise HTTPException(status_code=500, detail="教案生成失败，请稍后重试")


# ============ 异步生成任务（长请求治理 1C） ============
# generate-plan / culture-enrich 是 30-120 秒的同步 LLM 长请求，经 Next.js rewrites
# 代理转发时会被默认 30s proxyTimeout 掐断（浏览器 500、后端日志 200）。
# 改为 202 + task_id + 轮询；上方同步端点保留不动，作回滚开关。

_PLAN_TASKS: Dict[str, Dict[str, Any]] = {}
_PLAN_TASK_TTL_SECONDS = 3600


def _prune_plan_tasks() -> None:
    now = time.time()
    stale = [tid for tid, s in _PLAN_TASKS.items() if now - s.get("created_ts", now) > _PLAN_TASK_TTL_SECONDS]
    for tid in stale:
        _PLAN_TASKS.pop(tid, None)


async def _run_plan_generation(task_id: str, request: GeneratePlanRequest, current_user: dict) -> None:
    """generate-plan 后台流水线，与同步端点同构；同步步骤走 to_thread 避免阻塞事件循环"""
    state = _PLAN_TASKS[task_id]
    start_time = time.time()
    try:
        state.update(status="analyzing", progress="白盒分析中…")

        from app.services.analysis.whitebox_analyzer import WhiteboxAnalyzer
        from app.services.analysis.tag_generator import generate_tag_details, get_wiki_tags_for_retrieval, get_rag_tags_for_retrieval

        analyzer = WhiteboxAnalyzer()
        analysis_result = await asyncio.to_thread(
            analyzer.analyze, request.text, request.student_level, language=request.language
        )

        tag_details = generate_tag_details(analysis_result)
        wiki_tags = get_wiki_tags_for_retrieval(tag_details)
        rag_tags = get_rag_tags_for_retrieval(tag_details)

        analysis_dict = {
            "text_level": analysis_result.text_level,
            "language": analysis_result.language,
            "language_name": analysis_result.language_name,
            "vocabulary": {
                "total_words": analysis_result.vocabulary.total_words,
                "unique_words": analysis_result.vocabulary.unique_words,
                "cefr_distribution": analysis_result.vocabulary.cefr_distribution,
                "awl_count": analysis_result.vocabulary.awl_count,
                "awl_ratio": analysis_result.vocabulary.awl_ratio,
                "difficult_words": [
                    {"word": d.word, "level": d.level, "count": d.count, "in_awl": d.in_awl}
                    for d in analysis_result.vocabulary.difficult_words
                ],
                "vocabulary_richness": analysis_result.vocabulary.vocabulary_richness,
            },
            "syntax": {
                "total_sentences": analysis_result.syntax.total_sentences,
                "avg_sentence_length": analysis_result.syntax.avg_sentence_length,
                "max_sentence": {
                    "preview": analysis_result.syntax.max_sentence.preview,
                    "word_count": analysis_result.syntax.max_sentence.word_count,
                    "index": analysis_result.syntax.max_sentence.index,
                },
                "long_sentences_count": analysis_result.syntax.long_sentences_count,
                "very_long_sentences_count": analysis_result.syntax.very_long_sentences_count,
                "flesch_reading_ease": analysis_result.syntax.flesch_reading_ease,
            },
            "discourse": {
                "paragraph_count": analysis_result.discourse.paragraph_count,
                "connective_density": analysis_result.discourse.connective_density,
                "genre_hint": analysis_result.discourse.genre_hint,
                "text_structure": analysis_result.discourse.text_structure,
                "teaching_points": analysis_result.discourse.teaching_points,
            },
            "learner_gap": {
                "text_level": analysis_result.learner_gap.text_level,
                "student_level": analysis_result.learner_gap.student_level,
                "gap": analysis_result.learner_gap.gap,
                "gap_description": analysis_result.learner_gap.gap_description,
            },
            "enhancement_tags": analysis_result.enhancement_tags,
            "tag_labels": analysis_result.tag_labels,
            "teaching_insights": analysis_result.teaching_insights,
            "cultural_elements": [
                {"category": e.category, "keyword": e.keyword, "context": e.context, "explanation": e.explanation}
                for e in analysis_result.cultural_elements
            ],
            "teaching_tips": analysis_result.teaching_tips,
            "student_profile": {
                "native_language": request.native_language,
                "course_type": request.course_type,
                "class_size": request.class_size,
            },
        }

        logger.info(f"白盒分析完成: {analysis_result.text_level}, 标签{len(analysis_result.enhancement_tags)}个")

        state.update(status="retrieving", progress="双源检索中（教学理论 + 教学资源）…")

        from app.services.analysis.dual_retriever import DualRetriever

        retriever = DualRetriever()
        retrieval_result = await asyncio.to_thread(
            retriever.retrieve,
            wiki_tags=wiki_tags,
            rag_tags=rag_tags,
            enhancement_tags=analysis_result.enhancement_tags,
            text_title=request.title,
            max_wiki_results=request.max_retrieval_results,
            max_rag_results=request.max_retrieval_results,
        )

        wiki_results = [
            {
                "title": r.title,
                "summary": r.summary,
                "relevance_score": r.relevance_score,
                "tags": r.tags,
                "confidence": r.confidence,
                "contested": r.contested,
                "contradictions": r.contradictions,
                "sources": r.sources,
                "updated": r.updated,
            }
            for r in retrieval_result.wiki_results
        ]
        rag_results = [
            {
                "content": r.content,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in retrieval_result.rag_results
        ]

        logger.info(f"双源检索完成: Wiki={retrieval_result.wiki_count}, RAG={retrieval_result.rag_count}")

        state.update(status="generating", progress="AI 生成教学方案中…（约 30-120 秒）")

        from app.services.analysis.fusion_generator import generate_teaching_plan

        plan = await asyncio.to_thread(
            generate_teaching_plan,
            text_title=request.title or "Untitled",
            text_content=request.text,
            analysis=analysis_dict,
            wiki_results=wiki_results,
            rag_results=rag_results,
            mode=request.mode,
            duration_minutes=request.duration_minutes,
            course_type=request.course_type,
            class_size=request.class_size,
            native_language=request.native_language,
            teaching_intent=request.teaching_intent,
        )

        # 教学蓝图（仅增强模式单独展示）
        if request.mode == "enhanced":
            from app.services.analysis.blueprint import build_teaching_blueprint
            blueprint = build_teaching_blueprint(
                analysis_dict,
                {"activity_designs": plan.activity_designs},
                wiki_results,
                rag_results,
                request.duration_minutes,
            )
            evidence_annotations = plan.evidence_annotations
        else:
            blueprint = None
            evidence_annotations = None

        total_duration = time.time() - start_time

        response = {
            "text_title": request.title or "Untitled",
            "text_level": analysis_result.text_level,
            "language_name": analysis_result.language_name,
            "student_level": request.student_level,
            "learner_gap": analysis_dict["learner_gap"],
            "vocabulary": analysis_dict["vocabulary"],
            "cultural_elements": analysis_dict["cultural_elements"],
            "enhancement_tags": analysis_result.enhancement_tags,
            "tag_labels": analysis_result.tag_labels,
            "teaching_blueprint": blueprint,
            "teaching_plan": {
                "framework": plan.framework,
                "objectives": plan.objectives,
                "difficulty_overview": plan.difficulty_overview,
                "teaching_suggestions": plan.teaching_suggestions,
                "activity_designs": plan.activity_designs,
                "assessment": plan.assessment,
                "differentiation": plan.differentiation,
                "theoretical_basis": plan.theoretical_basis,
                "self_check": plan.self_check,
            },
            "evidence_annotations": evidence_annotations,
            "sources": plan.sources,
            "retrieval_info": {
                "wiki_count": retrieval_result.wiki_count,
                "rag_count": retrieval_result.rag_count,
                "retrieval_duration": retrieval_result.retrieval_duration,
            },
            "syntax": analysis_dict["syntax"],
            "discourse": analysis_dict["discourse"],
            "generation_settings": {
                "duration_minutes": request.duration_minutes,
                "course_type": request.course_type,
                "class_size": request.class_size,
                "native_language": request.native_language,
            },
            "generation_duration": plan.generation_duration,
            "total_duration": round(total_duration, 2),
            "model": plan.model,
            "prompt_version": plan.prompt_version,
            "fallback": plan.fallback,
        }

        # 生成记录落库：self_check 随产物保存，质量可追溯
        try:
            from app.models.generation import GenerationLog

            async with AsyncSessionLocal() as db:
                db.add(GenerationLog(
                    id=str(uuid.uuid4()),
                    user_id=current_user["user_id"],
                    analysis_id=None,
                    stage="lesson_plan",
                    prompt_name="lesson_plan_v2",
                    prompt_version=plan.prompt_version,
                    model=plan.model,
                    fallback="yes" if plan.fallback else "no",
                    generation_duration=plan.generation_duration,
                    self_check=plan.self_check or None,
                ))
                await db.commit()
        except Exception as log_err:
            logger.warning(f"生成记录落库失败（不影响返回）: {log_err}")

        # 教案版本落库（③ 历史恢复）：携带 analysis_id 时持久化，失败不影响任务结果
        if request.analysis_id:
            try:
                async with AsyncSessionLocal() as db:
                    await _persist_plan_version(db, request.analysis_id, current_user["user_id"], request.mode, response, teaching_intent=request.teaching_intent)
            except Exception as persist_err:
                logger.warning(f"教案版本落库失败（不影响返回）: {persist_err}")

        logger.info(f"教学方案生成完成: 总耗时{total_duration:.2f}s")
        state.update(status="done", result=response)

    except Exception as e:
        logger.error(f"教学方案生成失败: {e}")
        state.update(status="error", error="教案生成失败，请稍后重试")


async def _run_culture_enrichment(task_id: str, request: CultureEnrichRequest, current_user: dict) -> None:
    """culture-enrich 后台执行；失败保持同步端点降级语义（返回原元素 + fallback 标记，不报错）"""
    state = _PLAN_TASKS[task_id]
    try:
        state.update(status="enriching", progress="AI 生成文化背景补充中…（约 30-60 秒）")

        from app.services.analysis.culture_enricher import enrich_cultural_elements

        result = await asyncio.to_thread(
            enrich_cultural_elements,
            text=request.text,
            language_name=request.language_name,
            elements=request.cultural_elements,
        )
        state.update(status="done", result={
            "cultural_elements": result.items,
            "prompt_version": result.prompt_version,
            "model": result.model,
            "fallback": result.fallback,
            "self_check": result.self_check,
            "generation_duration": result.generation_duration,
        })
    except Exception as e:
        logger.error(f"文化背景具体化失败: {e}")
        state.update(status="done", result={
            "cultural_elements": request.cultural_elements,
            "prompt_version": "",
            "model": "template-fallback",
            "fallback": True,
            "self_check": {"error": str(e)},
            "generation_duration": 0,
        })


@router.post("/generate-plan-async", status_code=status.HTTP_202_ACCEPTED)
async def generate_teaching_plan_async(
    request: GeneratePlanRequest,
    current_user: dict = Depends(get_current_user),
):
    """启动教案生成后台任务，返回 task_id；轮询 GET /generation-tasks/{task_id}"""
    _prune_plan_tasks()
    task_id = uuid.uuid4().hex
    _PLAN_TASKS[task_id] = {
        "status": "pending",
        "progress": "已排队",
        "user_id": current_user["user_id"],
        "created_ts": time.time(),
    }
    asyncio.create_task(_run_plan_generation(task_id, request, current_user))
    return {"task_id": task_id}


@router.post("/culture-enrich-async", status_code=status.HTTP_202_ACCEPTED)
async def culture_enrich_async(
    request: CultureEnrichRequest,
    current_user: dict = Depends(get_current_user),
):
    """启动文化背景具体化后台任务，返回 task_id；轮询 GET /generation-tasks/{task_id}"""
    _prune_plan_tasks()
    task_id = uuid.uuid4().hex
    _PLAN_TASKS[task_id] = {
        "status": "pending",
        "progress": "已排队",
        "user_id": current_user["user_id"],
        "created_ts": time.time(),
    }
    asyncio.create_task(_run_culture_enrichment(task_id, request, current_user))
    return {"task_id": task_id}


@router.get("/generation-tasks/{task_id}")
async def get_generation_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """轮询异步生成任务状态（generate-plan-async / culture-enrich-async 共用）"""
    state = _PLAN_TASKS.get(task_id)
    if not state or state.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="生成任务不存在或已过期，请重新生成")
    return {
        "task_id": task_id,
        "status": state.get("status"),
        "progress": state.get("progress"),
        "result": state.get("result"),
        "error": state.get("error"),
    }


# ============ A/B 评价端点 ============

class ABEvaluationRequest(BaseModel):
    """A/B 评价请求"""
    chosen_version: str = Field(..., description="选择版本: baseline 或 enhanced", pattern=r"^(baseline|enhanced)$")
    rating: Optional[int] = Field(None, description="评分 1-5", ge=1, le=5)
    sentiment: Optional[str] = Field(None, description="赞成/反对: up 或 down", pattern=r"^(up|down)$")
    comment: Optional[str] = Field(None, description="评价内容")


@router.post("/ab-evaluate")
async def submit_ab_evaluation(
    request: ABEvaluationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """提交 A/B 两版评价"""
    from app.services.analysis.ab_evaluation import record_ab_evaluation

    try:
        result = await record_ab_evaluation(
            db,
            user_id=current_user["user_id"],
            chosen_version=request.chosen_version,
            rating=request.rating,
            sentiment=request.sentiment,
            comment=request.comment,
        )
        return result
    except Exception as e:
        raise handle_api_error(e, "A/B 评价提交")


# ============ 导出端点 ============

class ExportRequest(BaseModel):
    """导出请求"""
    format: str = Field("pptx", description="导出格式: pptx, docx 或 html")
    title: str = Field("教学方案", description="文档标题")
    plan: Dict[str, Any] = Field(..., description="教学方案数据")


@router.post("/export")
async def export_plan(
    request: ExportRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    导出教学方案为 PPT 或 Word 文档

    接收教学方案 JSON，返回文件流。
    """
    try:
        from app.services.analysis.export_service import export_pptx, export_docx, export_html
        from fastapi.responses import StreamingResponse

        if request.format == "pptx":
            buffer = export_pptx(request.plan, request.title)
            filename = f"{request.title}.pptx"
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        elif request.format == "docx":
            buffer = export_docx(request.plan, request.title)
            filename = f"{request.title}.docx"
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif request.format == "html":
            buffer = export_html(request.plan, request.title)
            filename = f"{request.title}.html"
            media_type = "text/html; charset=utf-8"
        else:
            raise HTTPException(status_code=400, detail=f"不支持的格式: {request.format}")

        # Sanitize filename to prevent header injection
        safe_filename = filename.replace('"', '').replace('\r', '').replace('\n', '').replace('\\', '')

        # HTTP 头只接受 latin-1，中文文件名直接放 header 会 500（latin-1 codec can't encode）。
        # 按 RFC 5987 双写：filename= 给老客户端的 ASCII 兜底名，filename*= 给 UTF-8 编码真名。
        ascii_fallback = f"lesson-plan.{request.format}"
        quoted_name = quote(safe_filename)

        logger.info(f"导出 {request.format}: {safe_filename}")

        return StreamingResponse(
            buffer,
            media_type=media_type,
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{quoted_name}'
                )
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出失败: {e}")
        raise HTTPException(status_code=500, detail="导出失败，请稍后重试")


# ============ 教案修订端点 ============

class RevisePlanRequest(BaseModel):
    """教案修订请求"""
    original_plan: Dict[str, Any] = Field(..., description="原始教案")
    revision_instruction: str = Field(..., min_length=2, max_length=500, description="教师修改意见")
    text: str = Field(..., min_length=20, description="原始课文")
    title: str = Field("", description="课文标题")
    student_level: str = Field("B1", pattern=r"^[A-C][12]$", description="学生CEFR水平")
    language: Optional[str] = Field(None, pattern=r"^[a-z]{2}$", description="语言代码")
    section_to_revise: Optional[str] = Field(None, description="要修改的部分: difficulty_overview/suggestions/activities/theory")


@router.post("/revise-plan")
async def revise_plan(
    request: RevisePlanRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    教案修订端点

    接收原始教案和教师修改意见，返回修订后的教案。
    """
    try:
        from app.services.analysis.plan_reviser import revise_teaching_plan

        revised = revise_teaching_plan(
            original_plan=request.original_plan,
            revision_instruction=request.revision_instruction,
            text=request.text,
            title=request.title,
            student_level=request.student_level,
            language=request.language,
            section_to_revise=request.section_to_revise,
        )

        response = {
            "teaching_plan": {
                "difficulty_overview": revised.difficulty_overview,
                "teaching_suggestions": revised.teaching_suggestions,
                "activity_designs": revised.activity_designs,
                "differentiation": revised.differentiation,
                "theoretical_basis": revised.theoretical_basis,
            },
            "revision_note": revised.revision_note,
            "generation_duration": revised.generation_duration,
            "model": revised.model,
            "self_check": revised.self_check,
            "prompt_version": revised.prompt_version,
            "fallback": revised.fallback,
        }

        logger.info(f"教案修订完成: 耗时{revised.generation_duration:.2f}s")
        return response

    except Exception as e:
        logger.error(f"教案修订失败: {e}")
        raise HTTPException(status_code=500, detail="教案修订失败，请稍后重试")


# ============ 教材对比分析端点 ============

class TextCompareItem(BaseModel):
    """单篇对比课文"""
    title: str = Field(..., max_length=200)
    text: str = Field(..., min_length=10)


class CompareTextsRequest(BaseModel):
    """教材对比分析请求"""
    texts: List[TextCompareItem] = Field(..., description="课文列表", min_length=2, max_length=5)
    student_level: str = Field("B1", pattern=r"^(A1|A2|B1|B2|C1|C2)$")


@router.post("/compare")
async def compare_texts(
    request: CompareTextsRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    教材对比分析端点

    对比多篇课文的难度指标，帮助教师选择合适的教材。
    """
    try:
        from app.services.analysis.whitebox_analyzer import WhiteboxAnalyzer

        analyzer = WhiteboxAnalyzer()
        results = []

        for item in request.texts:
            title = item.title
            text = item.text
            if len(text) < 20:
                results.append({"title": title, "error": "文本太短"})
                continue

            analysis = analyzer.analyze(text, request.student_level)
            results.append({
                "title": title,
                "text_level": analysis.text_level,
                "language": analysis.language,
                "language_name": analysis.language_name,
                "metrics": {
                    "total_words": analysis.vocabulary.total_words,
                    "unique_words": analysis.vocabulary.unique_words,
                    "vocabulary_richness": round(analysis.vocabulary.vocabulary_richness, 3),
                    "awl_ratio": round(analysis.vocabulary.awl_ratio, 3),
                    "avg_sentence_length": round(analysis.syntax.avg_sentence_length, 1),
                    "flesch_reading_ease": round(analysis.syntax.flesch_reading_ease, 1),
                    "long_sentences_count": analysis.syntax.long_sentences_count,
                    "connective_density": round(analysis.discourse.connective_density, 2),
                    "paragraph_count": analysis.discourse.paragraph_count,
                    "genre_hint": analysis.discourse.genre_hint,
                    "text_structure": analysis.discourse.text_structure,
                },
                "cefr_distribution": analysis.vocabulary.cefr_distribution,
                "difficult_words_count": len(analysis.vocabulary.difficult_words),
                "enhancement_tags": analysis.enhancement_tags,
                "tag_labels": analysis.tag_labels,
            })

        # 生成对比摘要
        if all("metrics" in r for r in results):
            levels = [r["text_level"] for r in results]
            word_counts = [r["metrics"]["total_words"] for r in results]
            difficulties = [r["metrics"]["flesch_reading_ease"] for r in results]

            summary = {
                "level_range": f"{min(levels)} ~ {max(levels)}",
                "word_count_range": f"{min(word_counts)} ~ {max(word_counts)}",
                "readability_range": f"{min(difficulties):.1f} ~ {max(difficulties):.1f}",
                "recommendation": _generate_comparison_recommendation(results, request.student_level),
            }
        else:
            summary = {"error": "部分文本分析失败，无法生成对比摘要"}

        return {
            "results": results,
            "summary": summary,
            "count": len(results),
        }

    except Exception as e:
        logger.error(f"教材对比分析失败: {e}")
        raise HTTPException(status_code=500, detail="对比分析失败，请稍后重试")


def _generate_comparison_recommendation(results: List[Dict], student_level: str) -> str:
    """基于对比结果生成推荐建议"""
    student_rank = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}.get(student_level, 3)

    recommendations = []
    for r in results:
        level = r["text_level"]
        level_rank = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}.get(level, 3)
        diff = level_rank - student_rank

        if diff <= 0:
            recommendations.append(f"「{r['title']}」（{level}）适合当前水平学生，可作为主教材")
        elif diff == 1:
            recommendations.append(f"「{r['title']}」（{level}）略高于学生水平，适合作为挑战性阅读材料")
        else:
            recommendations.append(f"「{r['title']}」（{level}）远高于学生水平，建议提供充分支架或降低使用优先级")

    return "；".join(recommendations)
