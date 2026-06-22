"""
双源并行检索器 - OutEye Edu 1.0 ADDSR-Lite

接收白盒分析的增强标签，并行从 Wiki（教学理论）和 RAG（教学资源）两个源检索。
Wiki 检索：基于 wiki_tags 查找教学理论和策略
RAG 检索：基于 rag_tags 查找教学案例和活动设计
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
import time

from .retrieval_planner import RetrievalPlanner


@dataclass
class WikiResult:
    """Wiki 检索结果"""
    page_name: str
    title: str
    summary: str
    relevance_score: float
    match_type: str
    tags: List[str]
    matched_sections: List[str]
    confidence: str = ""
    contested: bool = False
    contradictions: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    updated: str = ""


@dataclass
class RAGResult:
    """RAG 检索结果"""
    chunk_id: str
    content: str
    score: float
    doc_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DualRetrievalResult:
    """双源检索结果"""
    wiki_results: List[WikiResult]
    rag_results: List[RAGResult]
    wiki_query_used: str
    rag_query_used: str
    retrieval_duration: float
    wiki_count: int = 0
    rag_count: int = 0


# 标签到自然语言查询的映射
TAG_TO_WIKI_QUERY = {
    # 词汇相关
    "high_academic_vocab": "学术词汇教学 AWL 词汇习得策略",
    "very_high_academic_vocab": "高密度学术词汇 词汇教学法",
    "many_difficult_words": "超纲词处理 词汇支架 scaffolding",
    "moderate_difficult_words": "词汇预教学 pre-teaching",
    # 句法相关
    "very_long_sentences": "长难句分析 句法拆分 sentence parsing",
    "long_sentences_present": "复杂句教学 阅读理解策略",
    "dense_complex_syntax": "句法复杂度 句子简化策略",
    # 可读性相关
    "very_difficult_readability": "可读性 readability Flesch 分级阅读",
    "difficult_readability": "文本难度评估 阅读支架",
    # 语篇相关
    "high_connective_density": "连接词 语篇标记 cohesive devices",
    "argumentative_text": "议论文教学 argumentation 论证分析",
    "scientific_text": "学术语篇 科学文本阅读 EAP",
    # 学习者差距
    "i_plus_2_risk": "Krashen 输入假说 i+1 可理解输入",
    "i_plus_1_optimal": "最近发展区 ZPD 支架教学",
    # 词汇丰富度
    "high_lexical_diversity": "词汇丰富度 TTR 词汇多样性教学",
}

TAG_TO_RAG_QUERY = {
    # 词汇相关
    "high_academic_vocab": "学术词汇预习单 词汇教学活动设计",
    "very_high_academic_vocab": "词汇分层教学 差异化词汇任务",
    "many_difficult_words": "词汇支架活动 预教学词汇 词汇表设计",
    "moderate_difficult_words": "词汇练习 语境猜词策略",
    # 句法相关
    "very_long_sentences": "长句拆分练习 句法分析活动",
    "long_sentences_present": "句子成分分析 复杂句教学策略",
    "dense_complex_syntax": "句法简化 逐层理解活动",
    # 可读性相关
    "very_difficult_readability": "段落大意匹配 预读活动 scaffolding",
    "difficult_readability": "引导式阅读 阅读理解支架",
    # 语篇相关
    "high_connective_density": "连接词识别活动 语篇分析练习",
    "argumentative_text": "论点论据分析 议论文写作教学",
    "scientific_text": "学术文本阅读策略 研究论文教学",
    # 学习者差距
    "i_plus_2_risk": "双语词汇表 结构化阅读支架 差异化教学",
    "i_plus_1_optimal": "深层理解活动 批判性思维训练",
    # 词汇丰富度
    "high_lexical_diversity": "词汇扩展活动 同义词替换练习",
}


class DualRetriever:
    """双源并行检索器"""

    def __init__(self, wiki_root: Optional[str] = None):
        self.wiki_root = wiki_root
        self.planner = RetrievalPlanner()

    def retrieve(
        self,
        wiki_tags: List[str],
        rag_tags: List[str],
        enhancement_tags: List[str],
        text_title: str = "",
        max_wiki_results: int = 5,
        max_rag_results: int = 5,
    ) -> DualRetrievalResult:
        """
        并行从 Wiki 和 RAG 两个源检索

        Args:
            wiki_tags: Wiki 检索标签
            rag_tags: RAG 检索标签
            enhancement_tags: 增强标签（用于生成查询）
            text_title: 课文标题（可选，用于查询扩展）
            max_wiki_results: Wiki 最大结果数
            max_rag_results: RAG 最大结果数

        Returns:
            双源检索结果
        """
        start_time = time.time()

        # 生成查询计划
        plan = self.planner.build(
            wiki_tags=wiki_tags,
            rag_tags=rag_tags,
            enhancement_tags=enhancement_tags,
            text_title=text_title,
        )
        wiki_query = plan.wiki_query
        rag_query = plan.rag_query

        # 并行检索
        wiki_results = []
        rag_results = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {}
            if wiki_query:
                futures[executor.submit(self._search_wiki, wiki_query, max_wiki_results)] = "wiki"
            if rag_query:
                futures[executor.submit(self._search_rag, rag_query, max_rag_results)] = "rag"

            for future in as_completed(futures):
                source = futures[future]
                try:
                    result = future.result()
                    if source == "wiki":
                        wiki_results = result
                    elif source == "rag":
                        rag_results = result
                except Exception as e:
                    logger.warning(f"{source} 检索失败: {e}")

        duration = time.time() - start_time

        return DualRetrievalResult(
            wiki_results=wiki_results,
            rag_results=rag_results,
            wiki_query_used=wiki_query,
            rag_query_used=rag_query,
            retrieval_duration=round(duration, 2),
            wiki_count=len(wiki_results),
            rag_count=len(rag_results),
        )

    def _build_wiki_query(self, wiki_tags: List[str], enhancement_tags: List[str], title: str) -> str:
        """构建 Wiki 查询字符串"""
        queries = []
        for tag in wiki_tags:
            if tag in TAG_TO_WIKI_QUERY:
                queries.append(TAG_TO_WIKI_QUERY[tag])
            else:
                queries.append(tag.replace("_", " "))
        if not queries:
            # 回退：使用 enhancement_tags
            for tag in enhancement_tags[:3]:
                queries.append(tag.replace("_", " "))
        return " ".join(queries[:3])  # 最多3个查询词组合

    def _build_rag_query(self, rag_tags: List[str], enhancement_tags: List[str], title: str) -> str:
        """构建 RAG 查询字符串"""
        queries = []
        for tag in rag_tags:
            if tag in TAG_TO_RAG_QUERY:
                queries.append(TAG_TO_RAG_QUERY[tag])
            else:
                queries.append(tag.replace("_", " "))
        if not queries:
            for tag in enhancement_tags[:3]:
                queries.append(tag.replace("_", " "))
        return " ".join(queries[:3])

    # 缓存 WikiQuery 实例，避免每次请求重新解析整个 Wiki
    _wiki_service = None

    def _get_wiki_service(self):
        if DualRetriever._wiki_service is None:
            from app.services.wiki import WikiQuery
            from app.core.config import settings as cfg
            wiki_path = getattr(cfg, 'WIKI_DATA_PATH', None) or "../../OutEye-Wiki"
            DualRetriever._wiki_service = WikiQuery(wiki_root=wiki_path)
        return DualRetriever._wiki_service

    def _search_wiki(self, query: str, max_results: int) -> List[WikiResult]:
        """搜索 Wiki"""
        try:
            wiki_service = self._get_wiki_service()
            results = wiki_service.query(query, max_results=max_results)

            return [
                WikiResult(
                    page_name=r.page.filename,
                    title=r.page.frontmatter.title,
                    summary=r.page.content[:200] if r.page.content else "",
                    relevance_score=r.relevance_score,
                    match_type=r.match_type,
                    tags=r.page.frontmatter.tags if r.page.frontmatter.tags else [],
                    matched_sections=r.matched_sections,
                    confidence=r.page.frontmatter.confidence,
                    contested=r.page.frontmatter.contested,
                    contradictions=r.page.frontmatter.contradictions or [],
                    sources=r.page.frontmatter.sources or [],
                    updated=r.page.frontmatter.updated,
                )
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Wiki 搜索失败: {e}")
            return []

    def _search_rag(self, query: str, max_results: int) -> List[RAGResult]:
        """搜索 RAG"""
        try:
            from app.api.api_v1.endpoints.rag import get_rag_services

            services = get_rag_services()
            retriever = services['retriever']

            results = retriever.retrieve(query=query, method="hybrid", top_k=max_results)
            results = retriever.rerank(query=query, results=results, top_k=max_results)

            return [
                RAGResult(
                    chunk_id=r.chunk_id,
                    content=r.content[:300],  # 截断以控制响应大小
                    score=r.score,
                    doc_id=r.doc_id,
                    metadata=r.metadata,
                )
                for r in results
            ]
        except Exception as e:
            logger.warning(f"RAG 搜索失败: {e}")
            return []
