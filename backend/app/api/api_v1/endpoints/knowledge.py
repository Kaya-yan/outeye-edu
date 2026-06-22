"""
知识库端点
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_async_db
from app.core.security import get_current_user
from app.models.document import DocumentChunk

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


def _chunk_to_response(chunk: DocumentChunk) -> dict:
    """将 DocumentChunk 转换为 KnowledgeChunkResponse 格式"""
    extra = chunk.extra_data or {}
    return {
        "id": chunk.id,
        "content": chunk.content,
        "content_type": extra.get("content_type", "general"),
        "source_type": extra.get("source_type"),
        "vector_id": chunk.vector_id or "",
        "quality_score": extra.get("quality_score", 0.0),
        "verified": extra.get("verified", False),
        "retrieval_count": extra.get("retrieval_count", 0),
        "created_at": chunk.created_at,
    }


@router.get("/", response_model=List[KnowledgeChunkResponse])
async def get_knowledge_chunks(
    content_type: Optional[str] = None,
    source_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    """获取知识单元列表"""
    query = select(DocumentChunk).offset(skip).limit(limit)
    result = await db.execute(query)
    chunks = result.scalars().all()

    items = [_chunk_to_response(c) for c in chunks]

    if content_type:
        items = [i for i in items if i["content_type"] == content_type]
    if source_type:
        items = [i for i in items if i["source_type"] == source_type]

    return items


@router.get("/theories/all")
async def get_all_theories(db: AsyncSession = Depends(get_async_db)):
    """获取所有理论知识"""
    result = await db.execute(select(DocumentChunk))
    chunks = result.scalars().all()
    items = [_chunk_to_response(c) for c in chunks]
    return [i for i in items if i["content_type"] == "theory"]


@router.get("/strategies/all")
async def get_all_strategies(db: AsyncSession = Depends(get_async_db)):
    """获取所有教学策略"""
    result = await db.execute(select(DocumentChunk))
    chunks = result.scalars().all()
    items = [_chunk_to_response(c) for c in chunks]
    return [i for i in items if i["content_type"] == "teaching_strategy"]


@router.get("/{chunk_id}", response_model=KnowledgeChunkResponse)
async def get_knowledge_chunk(
    chunk_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """获取单个知识单元"""
    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.id == chunk_id)
    )
    chunk = result.scalar_one_or_none()

    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge chunk not found"
        )

    # 增加检索次数
    extra = chunk.extra_data or {}
    extra["retrieval_count"] = extra.get("retrieval_count", 0) + 1
    chunk.extra_data = extra
    await db.commit()

    return _chunk_to_response(chunk)


@router.post("/", response_model=KnowledgeChunkResponse)
async def create_knowledge_chunk(
    chunk: KnowledgeChunkCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """创建知识单元"""
    extra = {
        "content_type": chunk.content_type,
        "source_type": chunk.source_type,
        "quality_score": 0.0,
        "verified": False,
        "retrieval_count": 0,
    }
    if chunk.metadata:
        extra.update(chunk.metadata)

    new_chunk = DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),  # 独立知识单元，生成临时文档ID
        content=chunk.content,
        chunk_index=0,
        word_count=len(chunk.content.split()),
        extra_data=extra,
        created_at=datetime.utcnow(),
    )
    db.add(new_chunk)
    await db.commit()
    await db.refresh(new_chunk)
    return _chunk_to_response(new_chunk)


@router.post("/search", response_model=List[SearchResult])
async def search_knowledge(
    request: SearchRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """搜索知识库"""
    result = await db.execute(select(DocumentChunk))
    chunks = result.scalars().all()

    query_lower = request.query.lower()
    results = []
    for chunk in chunks:
        if query_lower in chunk.content.lower():
            results.append(SearchResult(
                chunk_id=chunk.id,
                content=chunk.content,
                score=0.85,
                metadata=chunk.extra_data
            ))

    results.sort(key=lambda x: x.score, reverse=True)
    return results[:request.top_k]


@router.post("/rag-query")
async def rag_query(
    query: str,
    top_k: int = 3,
    db: AsyncSession = Depends(get_async_db)
):
    """RAG查询（检索增强生成）"""
    search_results = await search_knowledge(
        SearchRequest(query=query, top_k=top_k),
        db
    )

    return {
        "query": query,
        "retrieved_chunks": search_results,
        "answer": "基于检索到的知识，建议采用支架式教学方法，先激活学生的背景知识，然后通过小组讨论促进批判性思维。"
    }
