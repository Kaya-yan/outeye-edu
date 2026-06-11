"""
文档模型
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Document(Base):
    """文档表"""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 文档信息
    title = Column(String(200), nullable=False)
    file_name = Column(String(200), nullable=True)
    file_type = Column(String(20), nullable=True)  # pdf, docx, txt, md
    file_size = Column(Integer, default=0)

    # 内容
    content = Column(Text, nullable=True)
    word_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)

    # 元数据
    extra_data = Column(JSON, nullable=True)
    status = Column(String(20), default="indexed")  # pending, indexing, indexed, error
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "word_count": self.word_count,
            "chunk_count": self.chunk_count,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class DocumentChunk(Base):
    """文档块表"""
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, index=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)

    # 块内容
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    word_count = Column(Integer, default=0)

    # 向量信息
    vector_id = Column(String(100), nullable=True)  # Qdrant 中的向量 ID
    embedding_model = Column(String(50), nullable=True)

    # 元数据
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    document = relationship("Document", back_populates="chunks")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "chunk_index": self.chunk_index,
            "word_count": self.word_count,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
