"""
Wiki查询端点
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.services.wiki import WikiQuery

router = APIRouter()

# Wiki根目录
WIKI_ROOT = "../../OutEye-Wiki"

# 初始化Wiki查询服务
wiki_query = None


def get_wiki_query():
    """获取Wiki查询服务实例"""
    global wiki_query
    if wiki_query is None:
        wiki_query = WikiQuery(WIKI_ROOT)
    return wiki_query


# Pydantic模型
class WikiSearchRequest(BaseModel):
    query: str
    max_results: int = 10


class WikiSearchResult(BaseModel):
    page_name: str
    title: str
    relevance_score: float
    match_type: str
    matched_sections: List[str]
    tags: List[str]
    summary: str


class TheoryNetwork(BaseModel):
    main_theory: Dict[str, Any]
    related_theories: List[Dict[str, Any]]
    network_size: int


class WikiStatistics(BaseModel):
    total_pages: int
    total_tags: int
    page_types: Dict[str, int]
    pages_with_backlinks: int
    average_wikilinks: float


@router.get("/search", response_model=List[WikiSearchResult])
async def search_wiki(
    query: str = Query(..., description="搜索关键词"),
    max_results: int = Query(10, description="最大结果数"),
    db: Session = Depends(get_db)
):
    """搜索Wiki"""
    wiki = get_wiki_query()
    results = wiki.query(query, max_results)

    return [
        WikiSearchResult(
            page_name=result.page.filename,
            title=result.page.frontmatter.title,
            relevance_score=result.relevance_score,
            match_type=result.match_type,
            matched_sections=result.matched_sections,
            tags=result.page.frontmatter.tags,
            summary=_get_summary(result.page)
        )
        for result in results
    ]


@router.get("/theory/{theory_name}", response_model=List[WikiSearchResult])
async def get_theory(
    theory_name: str,
    db: Session = Depends(get_db)
):
    """获取理论信息"""
    wiki = get_wiki_query()
    results = wiki.query_theory(theory_name)

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theory '{theory_name}' not found"
        )

    return [
        WikiSearchResult(
            page_name=result.page.filename,
            title=result.page.frontmatter.title,
            relevance_score=result.relevance_score,
            match_type=result.match_type,
            matched_sections=result.matched_sections,
            tags=result.page.frontmatter.tags,
            summary=_get_summary(result.page)
        )
        for result in results
    ]


@router.get("/theory/{theory_name}/network", response_model=TheoryNetwork)
async def get_theory_network(
    theory_name: str,
    db: Session = Depends(get_db)
):
    """获取理论网络"""
    wiki = get_wiki_query()
    network = wiki.get_theory_network(theory_name)

    if "error" in network:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=network["error"]
        )

    return network


@router.get("/analysis", response_model=List[WikiSearchResult])
async def get_analysis_theories(
    text_type: str = Query("academic", description="课文类型"),
    student_level: str = Query("B2", description="学生水平"),
    db: Session = Depends(get_db)
):
    """获取课文分析相关理论"""
    wiki = get_wiki_query()
    results = wiki.query_for_text_analysis(text_type, student_level)

    return [
        WikiSearchResult(
            page_name=result.page.filename,
            title=result.page.frontmatter.title,
            relevance_score=result.relevance_score,
            match_type=result.match_type,
            matched_sections=result.matched_sections,
            tags=result.page.frontmatter.tags,
            summary=_get_summary(result.page)
        )
        for result in results
    ]


@router.get("/lesson-plan", response_model=List[WikiSearchResult])
async def get_lesson_plan_theories(
    topic: str = Query(..., description="教学主题"),
    objectives: str = Query("", description="教学目标（逗号分隔）"),
    db: Session = Depends(get_db)
):
    """获取教案生成相关理论"""
    wiki = get_wiki_query()
    objective_list = [obj.strip() for obj in objectives.split(",") if obj.strip()]
    results = wiki.query_for_lesson_plan(topic, objective_list)

    return [
        WikiSearchResult(
            page_name=result.page.filename,
            title=result.page.frontmatter.title,
            relevance_score=result.relevance_score,
            match_type=result.match_type,
            matched_sections=result.matched_sections,
            tags=result.page.frontmatter.tags,
            summary=_get_summary(result.page)
        )
        for result in results
    ]


@router.get("/page/{page_name}")
async def get_page(
    page_name: str,
    db: Session = Depends(get_db)
):
    """获取Wiki页面详情"""
    wiki = get_wiki_query()
    page = wiki.parser.get_page(page_name)

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page '{page_name}' not found"
        )

    return {
        "name": page.filename,
        "title": page.frontmatter.title,
        "type": page.frontmatter.type,
        "tags": page.frontmatter.tags,
        "created": page.frontmatter.created,
        "updated": page.frontmatter.updated,
        "confidence": page.frontmatter.confidence,
        "content": page.content,
        "sections": page.sections,
        "wikilinks": page.wikilinks,
        "backlinks": page.backlinks
    }


@router.get("/tags", response_model=List[str])
async def get_all_tags(
    db: Session = Depends(get_db)
):
    """获取所有标签"""
    wiki = get_wiki_query()
    return wiki.parser.get_all_tags()


@router.get("/statistics", response_model=WikiStatistics)
async def get_statistics(
    db: Session = Depends(get_db)
):
    """获取Wiki统计信息"""
    wiki = get_wiki_query()
    stats = wiki.parser.get_statistics()

    return WikiStatistics(
        total_pages=stats["total_pages"],
        total_tags=stats["total_tags"],
        page_types=stats["page_types"],
        pages_with_backlinks=stats["pages_with_backlinks"],
        average_wikilinks=stats["average_wikilinks"]
    )


@router.post("/refresh")
async def refresh_wiki(
    db: Session = Depends(get_db)
):
    """刷新Wiki缓存"""
    global wiki_query
    wiki_query = None
    return {"message": "Wiki cache refreshed"}


def _get_summary(page, max_length: int = 200) -> str:
    """获取页面摘要"""
    # 获取第一个非空章节的内容
    for section_name, section_content in page.sections.items():
        if section_content and section_name != "introduction":
            # 截取前max_length个字符
            summary = section_content[:max_length]
            if len(section_content) > max_length:
                summary += "..."
            return summary

    # 如果没有找到，返回内容的前max_length个字符
    if page.content:
        summary = page.content[:max_length]
        if len(page.content) > max_length:
            summary += "..."
        return summary

    return ""