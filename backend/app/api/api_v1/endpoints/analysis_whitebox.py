"""
白盒分析API端点

提供透明、可验证的课文分析，输出教师能看懂的指标。
如果白盒分析失败，优雅回退到旧分析引擎。
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

class WhiteboxAnalysisRequest(BaseModel):
    """白盒分析请求"""
    text: str = Field(..., description="课文内容", min_length=20)
    title: str = Field("", description="课文标题")
    student_level: str = Field("B1", description="学生水平（CEFR）", pattern=r"^(A1|A2|B1|B2|C1|C2)$")
    language: Optional[str] = Field(None, description="指定语言代码（en/ja/fr/de/es/ko），为空则自动检测", pattern=r"^[a-z]{2}$")
    native_language: Optional[str] = Field(None, description="学生母语代码（如zh/ja/ko等）", pattern=r"^[a-z]{2}$")
    course_type: Optional[str] = Field(None, description="课程类型：精读/泛读/听说/写作/综合")
    class_size: Optional[int] = Field(None, description="班级人数", ge=1, le=200)


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
    max_retrieval_results: int = Field(3, description="每源最大检索数", ge=1, le=10)


@router.post("/generate-plan", response_model=Dict[str, Any])
async def generate_teaching_plan(
    request: GeneratePlanRequest,
    current_user: dict = Depends(get_current_user),
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
        )

        total_duration = time.time() - start_time

        response = {
            "text_title": request.title or "Untitled",
            "text_level": analysis_result.text_level,
            "student_level": request.student_level,
            "learner_gap": analysis_dict["learner_gap"],
            "enhancement_tags": analysis_result.enhancement_tags,
            "tag_labels": analysis_result.tag_labels,
            "teaching_plan": {
                "difficulty_overview": plan.difficulty_overview,
                "teaching_suggestions": plan.teaching_suggestions,
                "activity_designs": plan.activity_designs,
                "differentiation": plan.differentiation,
                "theoretical_basis": plan.theoretical_basis,
            },
            "sources": plan.sources,
            "retrieval_info": {
                "wiki_count": retrieval_result.wiki_count,
                "rag_count": retrieval_result.rag_count,
                "retrieval_duration": retrieval_result.retrieval_duration,
            },
            "generation_duration": plan.generation_duration,
            "total_duration": round(total_duration, 2),
            "model": plan.model,
        }

        logger.info(f"教学方案生成完成: 总耗时{total_duration:.2f}s")
        return response

    except Exception as e:
        logger.error(f"教学方案生成失败: {e}")
        raise HTTPException(status_code=500, detail="教案生成失败，请稍后重试")


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

        logger.info(f"导出 {request.format}: {safe_filename}")

        return StreamingResponse(
            buffer,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
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
