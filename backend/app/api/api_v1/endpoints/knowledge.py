"""
知识库端点
"""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from loguru import logger
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
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """获取知识单元列表（仅当前用户的 chunks；管理员可看全部）"""
    is_admin = current_user.get("is_admin", False)
    query = select(DocumentChunk).join(Document)
    if not is_admin:
        query = query.where(Document.user_id == current_user["user_id"])
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    chunks = result.scalars().all()

    items = [_chunk_to_response(c) for c in chunks]

    if content_type:
        items = [i for i in items if i["content_type"] == content_type]
    if source_type:
        items = [i for i in items if i["source_type"] == source_type]

    return items


@router.get("/theories/all")
async def get_all_theories(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """获取所有理论知识（仅当前用户的 chunks；管理员可看全部）"""
    is_admin = current_user.get("is_admin", False)
    query = select(DocumentChunk).join(Document)
    if not is_admin:
        query = query.where(Document.user_id == current_user["user_id"])
    result = await db.execute(query)
    chunks = result.scalars().all()
    items = [_chunk_to_response(c) for c in chunks]
    return [i for i in items if i["content_type"] == "theory"]


@router.get("/strategies/all")
async def get_all_strategies(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """获取所有教学策略（仅当前用户的 chunks；管理员可看全部）"""
    is_admin = current_user.get("is_admin", False)
    query = select(DocumentChunk).join(Document)
    if not is_admin:
        query = query.where(Document.user_id == current_user["user_id"])
    result = await db.execute(query)
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


class PublicKnowledgeItem(BaseModel):
    """公共资料条目（只读）"""
    id: str
    kind: str
    category: str
    title: str
    summary: str
    badge: str = "官方"
    source: str
    doc_type: Optional[str] = None
    created_at: Optional[str] = None


BUILTIN_PUBLIC_ASSETS = [
    {
        "id": "builtin-teaching-theories",
        "kind": "builtin",
        "category": "教学理论库",
        "title": "大学英语教学理论库",
        "summary": "覆盖产出导向法（POA）、任务型教学、输入假说、支架式教学等常用理论的核心要点与课堂应用方式。生成教案时自动作为理论依据被引用。",
        "badge": "官方",
        "source": "OutEye Edu 内置",
    },
    {
        "id": "builtin-cefr-wordlists",
        "kind": "builtin",
        "category": "CEFR 词表说明",
        "title": "CEFR 词汇分级体系说明",
        "summary": "平台采用主词表（约 3200 词）+ 词频频段词表（约 16400 词）两级判定课文词汇难度，未命中的低频词由 AI 按剑桥词典口径定级，课文分析中的等级徽章即来自该体系。",
        "badge": "官方",
        "source": "OutEye Edu 内置",
    },
    {
        "id": "builtin-culture-corpus",
        "kind": "builtin",
        "category": "文化语料分类",
        "title": "文化背景语料分类说明",
        "summary": "课文分析会识别节日、历史、制度、地理、文学、习俗等文化元素，并由 AI 补充具体事实背景与课堂应用建议，帮助教师快速准备文化讲解点。",
        "badge": "官方",
        "source": "OutEye Edu 内置",
    },
]


@router.get("/public", response_model=List[PublicKnowledgeItem])
async def get_public_knowledge(
    current_user: dict = Depends(get_current_user),
):
    """公共资料：内置知识资产说明 + 平台官方语料（只读，全员可见）"""
    items: list = [dict(a) for a in BUILTIN_PUBLIC_ASSETS]
    try:
        vector_store = _get_vector_store()
        docs: dict = {}
        for r in vector_store.get_all_records():
            payload = r.payload or {}
            if payload.get("scope") != "system":
                continue
            doc_id = payload.get("doc_id")
            if not doc_id or doc_id in docs:
                continue
            docs[doc_id] = {
                "id": doc_id,
                "kind": "document",
                "category": "官方语料",
                "title": payload.get("title", "") or "未命名文档",
                "summary": (payload.get("content") or "")[:200],
                "badge": "官方",
                "source": "平台官方语料",
                "doc_type": payload.get("doc_type") or "document",
                "created_at": payload.get("created_at"),
            }
        items.extend(docs.values())
    except Exception as e:
        logger.warning(f"公共语料聚合失败（仅返回内置资产）: {e}")
    return items


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
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """获取单个知识单元（仅所有者或管理员）"""
    # 用 join 直接取 user_id，避免 async session 中的 lazy load（MissingGreenlet）
    result = await db.execute(
        select(DocumentChunk, Document.user_id)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(DocumentChunk.id == chunk_id)
    )
    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge chunk not found"
        )

    chunk, owner_user_id = row

    # 权限检查：非管理员仅能查看自己的 chunks
    is_admin = current_user.get("is_admin", False)
    if not is_admin and owner_user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="无权访问该知识单元")

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
    """创建知识单元（绑定 owner_id = current_user.user_id）"""
    document_id = str(uuid.uuid4())
    new_doc = Document(
        id=document_id,
        user_id=current_user["user_id"],
        title=(chunk.content[:50] + "...") if len(chunk.content) > 50 else chunk.content,
        file_type="manual",
        file_size=0,
        word_count=len(chunk.content.split()),
        chunk_count=1,
        extra_data={"source_type": chunk.source_type} if chunk.source_type else {},
        status="indexed",
    )

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
        document_id=document_id,
        content=chunk.content,
        chunk_index=0,
        word_count=len(chunk.content.split()),
        extra_data=extra,
        created_at=datetime.utcnow(),
    )

    db.add(new_doc)
    db.add(new_chunk)
    await db.commit()
    await db.refresh(new_chunk)
    return _chunk_to_response(new_chunk)


async def _search_knowledge_internal(
    request: SearchRequest,
    current_user: dict,
    db: AsyncSession,
) -> List[SearchResult]:
    """内部搜索：按 user_id 过滤（管理员可搜全部）"""
    is_admin = current_user.get("is_admin", False)
    query = select(DocumentChunk).join(Document)
    if not is_admin:
        query = query.where(Document.user_id == current_user["user_id"])
    result = await db.execute(query)
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


@router.post("/search", response_model=List[SearchResult])
async def search_knowledge(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """搜索知识库（仅搜索当前用户的 chunks）"""
    return await _search_knowledge_internal(request, current_user, db)


@router.post("/rag-query")
async def rag_query(
    query: str,
    top_k: int = 3,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """RAG查询（仅基于当前用户的 chunks）"""
    search_results = await _search_knowledge_internal(
        SearchRequest(query=query, top_k=top_k), current_user, db
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
