"""
混合检索器

实现稠密检索、稀疏检索和RRF融合
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
import re
import math


@dataclass
class RetrievalResult:
    """检索结果"""
    chunk_id: str
    doc_id: str
    content: str
    score: float
    retrieval_method: str  # dense, sparse, hybrid
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class DocumentChunk:
    """文档块"""
    id: str
    doc_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, any] = field(default_factory=dict)


class HybridRetriever:
    """混合检索器"""

    def __init__(
        self,
        embedding_service=None,
        vector_store=None,
        top_k: int = 10,
        rrf_k: int = 60,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.top_k = top_k
        self.rrf_k = rrf_k
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight

        # 文档块索引（用于稀疏检索）
        self.chunks: Dict[str, DocumentChunk] = {}
        self.inverted_index: Dict[str, List[str]] = {}  # term -> chunk_ids

    def add_documents(self, chunks: List[DocumentChunk]):
        """
        添加文档块

        Args:
            chunks: 文档块列表
        """
        for chunk in chunks:
            self.chunks[chunk.id] = chunk

            # 构建倒排索引
            terms = self._tokenize(chunk.content)
            for term in terms:
                if term not in self.inverted_index:
                    self.inverted_index[term] = []
                if chunk.id not in self.inverted_index[term]:
                    self.inverted_index[term].append(chunk.id)

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        # 简单分词：按空格和标点分割
        text = text.lower()
        tokens = re.findall(r'\w+', text)

        # 中文分词（简化版）
        chinese_chars = re.findall(r'[一-鿿]+', text)
        for chars in chinese_chars:
            # 单字分词
            for char in chars:
                tokens.append(char)
            # 双字分词
            for i in range(len(chars) - 1):
                tokens.append(chars[i:i + 2])

        return tokens

    def retrieve(
        self,
        query: str,
        method: str = "hybrid",
        top_k: Optional[int] = None,
        filter_conditions: Optional[Dict] = None
    ) -> List[RetrievalResult]:
        """
        检索

        Args:
            query: 查询文本
            method: 检索方法（dense, sparse, hybrid）
            top_k: 返回数量
            filter_conditions: 过滤条件

        Returns:
            检索结果列表
        """
        if top_k is None:
            top_k = self.top_k

        if method == "dense":
            return self._dense_retrieve(query, top_k, filter_conditions)
        elif method == "sparse":
            return self._sparse_retrieve(query, top_k, filter_conditions)
        elif method == "hybrid":
            return self._hybrid_retrieve(query, top_k, filter_conditions)
        else:
            raise ValueError(f"不支持的检索方法: {method}")

    def _dense_retrieve(
        self,
        query: str,
        top_k: int,
        filter_conditions: Optional[Dict]
    ) -> List[RetrievalResult]:
        """稠密检索"""
        if not self.embedding_service or not self.vector_store:
            return []

        # 生成查询向量
        query_embedding = self.embedding_service.embed_text(query).embedding

        # 向量搜索
        search_results = self.vector_store.search(
            query_vector=query_embedding,
            top_k=top_k * 2,  # 获取更多结果用于重排序
            filter_conditions=filter_conditions
        )

        # 转换结果
        results = []
        for result in search_results:
            chunk_id = result.id
            if chunk_id in self.chunks:
                chunk = self.chunks[chunk_id]
                results.append(RetrievalResult(
                    chunk_id=chunk_id,
                    doc_id=chunk.doc_id,
                    content=chunk.content,
                    score=result.score,
                    retrieval_method="dense",
                    metadata=chunk.metadata
                ))

        return results[:top_k]

    def _sparse_retrieve(
        self,
        query: str,
        top_k: int,
        filter_conditions: Optional[Dict]
    ) -> List[RetrievalResult]:
        """稀疏检索（BM25）"""
        # 分词
        query_terms = self._tokenize(query)

        # 计算BM25分数
        scores: Dict[str, float] = {}

        # BM25参数
        k1 = 1.5
        b = 0.75

        # 计算平均文档长度
        doc_lengths = [len(self._tokenize(c.content)) for c in self.chunks.values()]
        avg_doc_len = sum(doc_lengths) / max(len(doc_lengths), 1)

        # 文档总数
        N = len(self.chunks)

        for term in query_terms:
            if term not in self.inverted_index:
                continue

            # 包含该词的文档数
            doc_freq = len(self.inverted_index[term])

            # IDF计算
            idf = math.log((N - doc_freq + 0.5) / (doc_freq + 0.5) + 1)

            for chunk_id in self.inverted_index[term]:
                if chunk_id not in self.chunks:
                    continue

                chunk = self.chunks[chunk_id]

                # 检查过滤条件
                if filter_conditions:
                    match = True
                    for key, value in filter_conditions.items():
                        if chunk.metadata.get(key) != value:
                            match = False
                            break
                    if not match:
                        continue

                # 词频
                content_lower = chunk.content.lower()
                term_freq = content_lower.count(term)

                # 文档长度
                doc_len = len(self._tokenize(chunk.content))

                # BM25分数
                tf = (term_freq * (k1 + 1)) / (term_freq + k1 * (1 - b + b * doc_len / avg_doc_len))
                score = idf * tf

                if chunk_id not in scores:
                    scores[chunk_id] = 0
                scores[chunk_id] += score

        # 排序
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # 构建结果
        results = []
        for chunk_id, score in sorted_results[:top_k * 2]:
            if chunk_id in self.chunks:
                chunk = self.chunks[chunk_id]

                # 归一化分数
                normalized_score = min(score / 10, 1.0)

                results.append(RetrievalResult(
                    chunk_id=chunk_id,
                    doc_id=chunk.doc_id,
                    content=chunk.content,
                    score=normalized_score,
                    retrieval_method="sparse",
                    metadata=chunk.metadata
                ))

        return results[:top_k]

    def _hybrid_retrieve(
        self,
        query: str,
        top_k: int,
        filter_conditions: Optional[Dict]
    ) -> List[RetrievalResult]:
        """混合检索（RRF融合）"""
        # 稠密检索
        dense_results = self._dense_retrieve(query, top_k * 2, filter_conditions)

        # 稀疏检索
        sparse_results = self._sparse_retrieve(query, top_k * 2, filter_conditions)

        # RRF融合
        rrf_scores: Dict[str, float] = {}
        result_map: Dict[str, RetrievalResult] = {}

        # 稠密检索RRF分数
        for rank, result in enumerate(dense_results):
            chunk_id = result.chunk_id
            rrf_score = 1.0 / (self.rrf_k + rank + 1)

            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = 0
            rrf_scores[chunk_id] += rrf_score * self.dense_weight

            result_map[chunk_id] = result

        # 稀疏检索RRF分数
        for rank, result in enumerate(sparse_results):
            chunk_id = result.chunk_id
            rrf_score = 1.0 / (self.rrf_k + rank + 1)

            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = 0
            rrf_scores[chunk_id] += rrf_score * self.sparse_weight

            if chunk_id not in result_map:
                result_map[chunk_id] = result

        # 排序
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # 构建结果
        results = []
        for chunk_id, score in sorted_results[:top_k]:
            if chunk_id in result_map:
                result = result_map[chunk_id]
                results.append(RetrievalResult(
                    chunk_id=result.chunk_id,
                    doc_id=result.doc_id,
                    content=result.content,
                    score=score,
                    retrieval_method="hybrid",
                    metadata=result.metadata
                ))

        return results

    def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        重排序

        Args:
            query: 查询文本
            results: 检索结果
            top_k: 返回数量

        Returns:
            重排序后的结果
        """
        # 简化版重排序：基于查询词匹配度
        query_terms = set(self._tokenize(query))

        reranked = []
        for result in results:
            # 计算词匹配度
            content_terms = set(self._tokenize(result.content))
            overlap = len(query_terms & content_terms)
            match_ratio = overlap / max(len(query_terms), 1)

            # 综合分数
            combined_score = result.score * 0.7 + match_ratio * 0.3

            reranked.append(RetrievalResult(
                chunk_id=result.chunk_id,
                doc_id=result.doc_id,
                content=result.content,
                score=combined_score,
                retrieval_method=result.retrieval_method,
                metadata=result.metadata
            ))

        # 排序
        reranked.sort(key=lambda x: x.score, reverse=True)

        return reranked[:top_k]

    def expand_query(self, query: str) -> List[str]:
        """
        查询扩展

        Args:
            query: 原始查询

        Returns:
            扩展后的查询列表
        """
        expanded = [query]

        # 同义词扩展（简化版）
        synonyms = {
            "教学": ["教育", "授课", "讲授"],
            "学习": ["研修", "修习", "学习"],
            "分析": ["解析", "剖析", "研究"],
            "理论": ["学说", "原理", "理论"],
            "方法": ["方式", "手段", "途径"]
        }

        query_terms = self._tokenize(query)
        for term in query_terms:
            if term in synonyms:
                for synonym in synonyms[term]:
                    expanded_query = query.replace(term, synonym)
                    expanded.append(expanded_query)

        return list(set(expanded))
