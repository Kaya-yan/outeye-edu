"""
知识库端点
"""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_async_db
from app.core.security import get_current_user
from app.models.document import Document, DocumentChunk

router = APIRouter()

# 知识库文件上传上限（20MB）
KNOWLEDGE_MAX_UPLOAD_SIZE = 20 * 1024 * 1024
# 知识库允许的扩展名
KNOWLEDGE_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


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


class KnowledgeDocumentResponse(BaseModel):
    """知识文档列表项"""
    id: str
    title: str
    source: str
    doc_type: str
    tags: List[str]
    summary: str
    status: str
    created_at: Optional[str] = None


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


def _get_vector_store():
    """获取向量库实例（不加载 Embedding 模型）"""
    from urllib.parse import urlparse
    from app.core.config import settings
    from app.services.rag.vector_store import VectorStore

    qdrant_url = getattr(settings, "QDRANT_URL", "http://localhost:6333")
    parsed = urlparse(qdrant_url)
    return VectorStore(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6333,
        collection_name=getattr(settings, "QDRANT_COLLECTION", "outeye_knowledge"),
        vector_size=getattr(settings, "EMBEDDING_DIMENSION", 384),
    )


@router.get("", response_model=List[KnowledgeChunkResponse])
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


@router.get("/documents", response_model=List[KnowledgeDocumentResponse])
async def list_knowledge_documents(
    scope: str = "system",
    current_user: dict = Depends(get_current_user),
):
    """列出知识文档（system 全员可见 / private 仅当前用户）"""
    if scope not in ("system", "private"):
        raise HTTPException(status_code=400, detail="scope 必须为 system 或 private")

    vector_store = _get_vector_store()
    records = vector_store.get_all_records()

    filtered = []
    for r in records:
        payload = r.payload or {}
        if scope == "system":
            if payload.get("scope") == "system":
                filtered.append(payload)
        else:
            if (
                payload.get("scope") == "private"
                and payload.get("owner_id") == current_user["user_id"]
            ):
                filtered.append(payload)

    docs = {}
    for payload in filtered:
        doc_id = payload.get("doc_id")
        if not doc_id or doc_id in docs:
            continue
        source = payload.get("source", "user_upload")
        docs[doc_id] = {
            "id": doc_id,
            "title": payload.get("title", ""),
            "source": source,
            "doc_type": payload.get("doc_type") or (
                "theory" if source == "system_seed" else "document"
            ),
            "tags": payload.get("tags", []),
            "summary": (payload.get("content") or "")[:200],
            "status": "indexed",
            "created_at": payload.get("created_at"),
        }

    return list(docs.values())


@router.delete("/documents/{document_id}")
async def delete_knowledge_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """删除知识文档（仅所有者或管理员）"""
    vector_store = _get_vector_store()
    records = vector_store.get_all_records()

    matching = [r for r in records if (r.payload or {}).get("doc_id") == document_id]
    if not matching:
        raise HTTPException(status_code=404, detail="文档不存在")

    first_payload = matching[0].payload or {}
    scope = first_payload.get("scope", "private")
    owner_id = first_payload.get("owner_id")

    is_admin = current_user.get("is_admin", False)
    if not is_admin:
        if scope != "private" or owner_id != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="无权删除该文档")

    # 清理 Qdrant 中该文档的全部 points
    chunk_ids = [r.id for r in matching]
    vector_store.delete(chunk_ids)

    # 防御性清理 PostgreSQL（先子表后主表，命中 0 行也不报错）
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    await db.execute(delete(Document).where(Document.id == document_id))
    await db.commit()

    return {"success": True, "deleted_chunks": len(chunk_ids)}


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


@router.post("", response_model=KnowledgeChunkResponse)
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


class KnowledgeUploadResponse(BaseModel):
    """知识库文件上传响应"""
    document_id: str
    status: str


@router.post("/upload", response_model=KnowledgeUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_knowledge_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """上传知识文件（异步入队，返回 document_id 供轮询）"""
    suffix = os.path.splitext(file.filename or "")[1].lower()

    if suffix == ".doc":
        raise HTTPException(
            status_code=400,
            detail="不支持旧版 .doc 格式，请先另存为 .docx 后再上传",
        )
    if suffix not in KNOWLEDGE_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {suffix}，支持: {sorted(KNOWLEDGE_ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > KNOWLEDGE_MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制（上限 20MB）",
        )

    from app.services.ingestion.queue import ingestion_queue
    from app.services.ingestion.jobs import IngestionJob

    document_id = str(uuid.uuid4())
    job = IngestionJob(
        id=document_id,
        payload={
            "type": "file",
            "document_id": document_id,
            "filename": file.filename,
            "content_bytes": content,
            "current_user": current_user,
        },
        user_id=current_user["user_id"],
    )
    await ingestion_queue.submit(job)

    return KnowledgeUploadResponse(document_id=document_id, status="queued")
