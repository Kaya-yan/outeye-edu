"""
知识库端点
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db

router = APIRouter()


# Pydantic模型
class KnowledgeChunkCreate(BaseModel):
    content: str
    content_type: str
    source_type: Optional[str] = None
    metadata: Optional[dict] = None


class KnowledgeChunkResponse(BaseModel):
    id: str
    content: str
    content_type: str
    source_type: Optional[str]
    vector_id: str
    quality_score: float
    verified: bool
    retrieval_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: Optional[dict] = None


class SearchResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: Optional[dict]


# 示例知识单元数据
SAMPLE_KNOWLEDGE_CHUNKS = [
    {
        "id": "1",
        "content": "Krashen的输入假说认为，学习者需要接触略高于当前水平的输入（i+1），才能促进语言习得。这个理论强调可理解性输入的重要性。",
        "content_type": "theory",
        "source_type": "academic_paper",
        "vector_id": "vec_001",
        "quality_score": 0.95,
        "verified": True,
        "retrieval_count": 45,
        "created_at": "2026-01-01T00:00:00"
    },
    {
        "id": "2",
        "content": "Bloom认知分类学将认知过程分为六个层级：记忆、理解、应用、分析、评价、创造。教学设计应覆盖所有层级。",
        "content_type": "theory",
        "source_type": "textbook",
        "vector_id": "vec_002",
        "quality_score": 0.95,
        "verified": True,
        "retrieval_count": 38,
        "created_at": "2026-01-01T00:00:00"
    },
    {
        "id": "3",
        "content": "CEFR（欧洲语言共同参考框架）将语言能力分为A1、A2、B1、B2、C1、C2六个等级，从初学者到精通者。",
        "content_type": "framework",
        "source_type": "official_document",
        "vector_id": "vec_003",
        "quality_score": 0.95,
        "verified": True,
        "retrieval_count": 60,
        "created_at": "2026-01-01T00:00:00"
    },
    {
        "id": "4",
        "content": "认知负荷理论区分了三种认知负荷：内在认知负荷（由学习材料本身决定）、外在认知负荷（由教学设计不当引起）、相关认知负荷（促进学习的认知处理）。",
        "content_type": "theory",
        "source_type": "academic_paper",
        "vector_id": "vec_004",
        "quality_score": 0.92,
        "verified": True,
        "retrieval_count": 32,
        "created_at": "2026-01-01T00:00:00"
    },
    {
        "id": "5",
        "content": "在环保主题课文教学中，建议使用新闻视频作为导入活动，激活学生的背景知识，然后通过小组讨论促进批判性思维。",
        "content_type": "teaching_strategy",
        "source_type": "expert_interview",
        "vector_id": "vec_005",
        "quality_score": 0.88,
        "verified": True,
        "retrieval_count": 25,
        "created_at": "2026-02-15T00:00:00"
    }
]


@router.get("/", response_model=List[KnowledgeChunkResponse])
async def get_knowledge_chunks(
    content_type: Optional[str] = None,
    source_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取知识单元列表"""
    chunks = SAMPLE_KNOWLEDGE_CHUNKS

    # 按内容类型过滤
    if content_type:
        chunks = [c for c in chunks if c["content_type"] == content_type]

    # 按来源类型过滤
    if source_type:
        chunks = [c for c in chunks if c["source_type"] == source_type]

    return chunks[skip:skip + limit]


@router.get("/theories/all")
async def get_all_theories(
    db: Session = Depends(get_db)
):
    """获取所有理论知识"""
    theories = [c for c in SAMPLE_KNOWLEDGE_CHUNKS if c["content_type"] == "theory"]
    return theories


@router.get("/strategies/all")
async def get_all_strategies(
    db: Session = Depends(get_db)
):
    """获取所有教学策略"""
    strategies = [c for c in SAMPLE_KNOWLEDGE_CHUNKS if c["content_type"] == "teaching_strategy"]
    return strategies


@router.get("/{chunk_id}", response_model=KnowledgeChunkResponse)
async def get_knowledge_chunk(
    chunk_id: str,
    db: Session = Depends(get_db)
):
    """获取单个知识单元"""
    for chunk in SAMPLE_KNOWLEDGE_CHUNKS:
        if chunk["id"] == chunk_id:
            # 增加检索次数
            chunk["retrieval_count"] += 1
            return chunk
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Knowledge chunk not found"
    )


@router.post("/", response_model=KnowledgeChunkResponse)
async def create_knowledge_chunk(
    chunk: KnowledgeChunkCreate,
    db: Session = Depends(get_db)
):
    """创建知识单元"""
    new_chunk = {
        "id": str(len(SAMPLE_KNOWLEDGE_CHUNKS) + 1),
        "content": chunk.content,
        "content_type": chunk.content_type,
        "source_type": chunk.source_type,
        "vector_id": f"vec_{len(SAMPLE_KNOWLEDGE_CHUNKS) + 1:03d}",
        "quality_score": 0.0,
        "verified": False,
        "retrieval_count": 0,
        "created_at": datetime.now().isoformat()
    }
    SAMPLE_KNOWLEDGE_CHUNKS.append(new_chunk)
    return new_chunk


@router.post("/search", response_model=List[SearchResult])
async def search_knowledge(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """搜索知识库（RAG检索）"""
    # 示例实现：简单关键词搜索
    # 实际应用中应调用Qdrant进行向量检索
    results = []
    query_lower = request.query.lower()

    for chunk in SAMPLE_KNOWLEDGE_CHUNKS:
        # 简单的关键词匹配
        if query_lower in chunk["content"].lower():
            results.append({
                "chunk_id": chunk["id"],
                "content": chunk["content"],
                "score": 0.85,  # 示例分数
                "metadata": {
                    "content_type": chunk["content_type"],
                    "source_type": chunk["source_type"]
                }
            })

    # 按分数排序
    results.sort(key=lambda x: x["score"], reverse=True)

    # 返回Top-K结果
    return results[:request.top_k]


@router.post("/rag-query")
async def rag_query(
    query: str,
    top_k: int = 3,
    db: Session = Depends(get_db)
):
    """RAG查询（检索增强生成）"""
    # 示例实现：返回检索结果
    # 实际应用中应：
    # 1. 查询扩展
    # 2. 混合检索（稠密+稀疏）
    # 3. RRF融合
    # 4. 重排序
    # 5. 注入Prompt生成答案

    # 简化版：直接返回检索结果
    search_results = await search_knowledge(
        SearchRequest(query=query, top_k=top_k),
        db
    )

    return {
        "query": query,
        "retrieved_chunks": search_results,
        "answer": "基于检索到的知识，建议采用支架式教学方法，先激活学生的背景知识，然后通过小组讨论促进批判性思维。"
    }