"""
RAG API端点

提供检索增强生成相关的API接口
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel, Field
from loguru import logger

from app.utils.error_handler import handle_api_error

router = APIRouter()


# ============ 请求/响应模型 ============

class DocumentUploadRequest(BaseModel):
    """文档上传请求"""
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="文档内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class RAGQueryRequest(BaseModel):
    """RAG查询请求"""
    query: str = Field(..., description="查询文本")
    method: str = Field("hybrid", description="检索方法：dense, sparse, hybrid")
    top_k: int = Field(5, description="返回结果数量", ge=1, le=20)
    use_wiki: bool = Field(True, description="是否使用Wiki知识库")
    filter_conditions: Optional[Dict[str, Any]] = Field(None, description="过滤条件")


class RAGQueryResponse(BaseModel):
    """RAG查询响应"""
    answer: str = Field(..., description="生成的回答")
    sources: List[Dict[str, Any]] = Field(..., description="参考来源")
    confidence: float = Field(..., description="置信度")
    response_time: float = Field(..., description="响应时间（秒）")
    model: str = Field(..., description="使用的模型")


class DocumentChunkResponse(BaseModel):
    """文档块响应"""
    id: str
    doc_id: str
    content: str
    metadata: Dict[str, Any]


class CollectionStatsResponse(BaseModel):
    """集合统计响应"""
    total_documents: int
    total_chunks: int
    collection_name: str
    status: str


# ============ 服务初始化 ============

# 延迟初始化服务
_rag_engine = None
_document_parser = None
_embedding_service = None
_vector_store = None
_retriever = None
_generator = None


def get_rag_services():
    """获取RAG服务实例"""
    global _rag_engine, _document_parser, _embedding_service, _vector_store, _retriever, _generator

    if _document_parser is None:
        from app.services.rag import (
            DocumentParser,
            EmbeddingService,
            VectorStore,
            HybridRetriever,
            RAGGenerator
        )
        from app.core.config import settings

        _document_parser = DocumentParser()
        _embedding_service = EmbeddingService(
            model_name=getattr(settings, 'EMBEDDING_MODEL', 'bge-large-zh'),
            api_key=getattr(settings, 'EMBEDDING_API_KEY', None),
            api_base=getattr(settings, 'EMBEDDING_API_BASE', None)
        )
        _vector_store = VectorStore(
            host=getattr(settings, 'QDRANT_HOST', 'localhost'),
            port=getattr(settings, 'QDRANT_PORT', 6333),
            collection_name=getattr(settings, 'QDRANT_COLLECTION', 'outeye_documents'),
            vector_size=getattr(settings, 'VECTOR_SIZE', 1024)
        )
        _retriever = HybridRetriever(
            embedding_service=_embedding_service,
            vector_store=_vector_store
        )
        _generator = RAGGenerator(
            api_key=getattr(settings, 'LLM_API_KEY', None),
            api_base=getattr(settings, 'LLM_API_BASE', None),
            model=getattr(settings, 'LLM_MODEL', 'deepseek-chat')
        )

    return {
        'parser': _document_parser,
        'embedding': _embedding_service,
        'vector_store': _vector_store,
        'retriever': _retriever,
        'generator': _generator
    }


# ============ API端点 ============

@router.post("/upload", response_model=Dict[str, Any])
async def upload_document(request: DocumentUploadRequest):
    """
    上传文档

    上传文档内容，进行解析、分块和向量化
    """
    try:
        services = get_rag_services()
        parser = services['parser']
        embedding = services['embedding']
        vector_store = services['vector_store']
        retriever = services['retriever']

        # 解析文档
        doc = parser.parse_text(
            text=request.content,
            title=request.title,
            metadata=request.metadata
        )

        # 生成Embedding并存储（只计算一次）
        from app.services.rag.vector_store import VectorRecord
        from app.services.rag.retriever import DocumentChunk as RetrieverChunk

        records = []
        retriever_chunks = []

        for chunk in doc.chunks:
            # 生成Embedding（只计算一次）
            embed_result = embedding.embed_text(chunk.content)
            embedding_vector = embed_result.embedding

            # 创建向量记录
            record = VectorRecord(
                id=chunk.id,
                vector=embedding_vector,
                payload={
                    'doc_id': chunk.doc_id,
                    'content': chunk.content,
                    'title': request.title,
                    'metadata': chunk.metadata
                }
            )
            records.append(record)

            # 创建检索器块
            retriever_chunks.append(RetrieverChunk(
                id=chunk.id,
                doc_id=chunk.doc_id,
                content=chunk.content,
                embedding=embedding_vector,
                metadata=chunk.metadata
            ))

        # 存储到向量数据库
        success = vector_store.upsert(records)

        if not success:
            raise HTTPException(status_code=500, detail="向量存储失败")

        # 添加到检索器
        retriever.add_documents(retriever_chunks)

        logger.info(f"文档上传成功: {request.title}, {len(doc.chunks)} 个块")

        return {
            "success": True,
            "document_id": doc.id,
            "title": doc.title,
            "chunks_count": len(doc.chunks),
            "message": f"文档 '{request.title}' 上传成功，已分为 {len(doc.chunks)} 个块"
        }

    except Exception as e:
        raise handle_api_error(e, "文档上传")


@router.post("/upload-file", response_model=Dict[str, Any])
async def upload_file(file: UploadFile = File(...)):
    """
    上传文件

    支持PDF、Word、Markdown、TXT等格式
    """
    try:
        services = get_rag_services()
        parser = services['parser']
        embedding = services['embedding']
        vector_store = services['vector_store']
        retriever = services['retriever']

        # 检查文件扩展名
        from app.core.config import settings
        import os

        suffix = os.path.splitext(file.filename)[1].lower()
        if suffix not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {suffix}，支持的格式: {settings.ALLOWED_EXTENSIONS}"
            )

        # 检查文件大小
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制: {len(content)} > {settings.MAX_UPLOAD_SIZE}"
            )

        # 保存临时文件
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # 解析文件
            doc = parser.parse_file(tmp_path)

            # 生成Embedding并存储（只计算一次）
            from app.services.rag.vector_store import VectorRecord
            from app.services.rag.retriever import DocumentChunk as RetrieverChunk

            records = []
            retriever_chunks = []

            for chunk in doc.chunks:
                # 生成Embedding（只计算一次）
                embed_result = embedding.embed_text(chunk.content)
                embedding_vector = embed_result.embedding

                # 创建向量记录
                record = VectorRecord(
                    id=chunk.id,
                    vector=embedding_vector,
                    payload={
                        'doc_id': chunk.doc_id,
                        'content': chunk.content,
                        'title': doc.title,
                        'file_name': file.filename,
                        'metadata': chunk.metadata
                    }
                )
                records.append(record)

                # 创建检索器块
                retriever_chunks.append(RetrieverChunk(
                    id=chunk.id,
                    doc_id=chunk.doc_id,
                    content=chunk.content,
                    embedding=embedding_vector,
                    metadata=chunk.metadata
                ))

            # 存储
            success = vector_store.upsert(records)

            if not success:
                raise HTTPException(status_code=500, detail="向量存储失败")

            # 添加到检索器
            retriever.add_documents(retriever_chunks)

            logger.info(f"文件上传成功: {file.filename}, {len(doc.chunks)} 个块")

            return {
                "success": True,
                "document_id": doc.id,
                "title": doc.title,
                "file_name": file.filename,
                "chunks_count": len(doc.chunks),
                "message": f"文件 '{file.filename}' 上传成功，已分为 {len(doc.chunks)} 个块"
            }

        finally:
            # 清理临时文件
            os.unlink(tmp_path)

    except Exception as e:
        raise handle_api_error(e, "文件上传")


@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(request: RAGQueryRequest):
    """
    RAG查询

    基于检索结果生成回答
    """
    try:
        services = get_rag_services()
        retriever = services['retriever']
        generator = services['generator']

        # 检索
        retrieval_results = retriever.retrieve(
            query=request.query,
            method=request.method,
            top_k=request.top_k,
            filter_conditions=request.filter_conditions
        )

        # 重排序
        retrieval_results = retriever.rerank(
            query=request.query,
            results=retrieval_results,
            top_k=request.top_k
        )

        # 生成回答
        result = generator.generate(
            query=request.query,
            retrieval_results=retrieval_results,
            include_sources=True
        )

        logger.info(f"RAG查询完成: {request.query[:50]}...")

        return RAGQueryResponse(
            answer=result.answer,
            sources=result.sources,
            confidence=result.confidence,
            response_time=result.response_time,
            model=result.model
        )

    except Exception as e:
        raise handle_api_error(e, "RAG查询")


@router.post("/query-with-wiki", response_model=RAGQueryResponse)
async def query_with_wiki(request: RAGQueryRequest):
    """
    Wiki + RAG联合查询

    结合Wiki知识库和RAG检索生成回答
    """
    try:
        services = get_rag_services()
        retriever = services['retriever']
        generator = services['generator']

        # Wiki查询
        wiki_results = []
        if request.use_wiki:
            try:
                from app.services.wiki import WikiQuery
                wiki_service = WikiQuery(wiki_path="OutEye-Wiki")
                wiki_results = wiki_service.search(request.query, limit=3)
            except Exception as e:
                logger.warning(f"Wiki查询失败: {e}")

        # RAG检索
        retrieval_results = retriever.retrieve(
            query=request.query,
            method=request.method,
            top_k=request.top_k,
            filter_conditions=request.filter_conditions
        )

        # 重排序
        retrieval_results = retriever.rerank(
            query=request.query,
            results=retrieval_results,
            top_k=request.top_k
        )

        # 生成回答
        result = generator.generate_with_wiki(
            query=request.query,
            wiki_results=wiki_results,
            rag_results=retrieval_results
        )

        logger.info(f"Wiki+RAG查询完成: {request.query[:50]}...")

        return RAGQueryResponse(
            answer=result.answer,
            sources=result.sources,
            confidence=result.confidence,
            response_time=result.response_time,
            model=result.model
        )

    except Exception as e:
        raise handle_api_error(e, "Wiki+RAG查询")


@router.get("/stats", response_model=CollectionStatsResponse)
async def get_collection_stats():
    """
    获取向量集合统计信息
    """
    try:
        services = get_rag_services()
        vector_store = services['vector_store']

        info = vector_store.get_collection_info()

        return CollectionStatsResponse(
            total_documents=info.get('points_count', 0),
            total_chunks=info.get('vectors_count', 0),
            collection_name=info.get('name', ''),
            status=info.get('status', 'unknown')
        )

    except Exception as e:
        raise handle_api_error(e, "获取统计信息")


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """
    删除文档

    删除指定文档的所有块
    """
    try:
        services = get_rag_services()
        vector_store = services['vector_store']

        # 获取文档的所有块ID
        # 这里简化处理，实际应该查询获取
        success = vector_store.delete([doc_id])

        if success:
            logger.info(f"文档已删除: {doc_id}")
            return {"success": True, "message": f"文档 {doc_id} 已删除"}
        else:
            raise HTTPException(status_code=500, detail="删除失败")

    except Exception as e:
        raise handle_api_error(e, "删除文档")


@router.post("/search-similar", response_model=List[DocumentChunkResponse])
async def search_similar(
    text: str,
    top_k: int = 5
):
    """
    搜索相似文档块

    基于文本内容搜索相似的文档块
    """
    try:
        services = get_rag_services()
        embedding = services['embedding']
        vector_store = services['vector_store']

        # 生成查询向量
        embed_result = embedding.embed_text(text)

        # 搜索
        results = vector_store.search(
            query_vector=embed_result.embedding,
            top_k=top_k
        )

        # 转换结果
        chunks = []
        for result in results:
            chunks.append(DocumentChunkResponse(
                id=result.id,
                doc_id=result.payload.get('doc_id', ''),
                content=result.payload.get('content', ''),
                metadata=result.payload
            ))

        return chunks

    except Exception as e:
        raise handle_api_error(e, "搜索相似文档")
