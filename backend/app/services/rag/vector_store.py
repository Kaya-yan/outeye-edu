"""
向量存储服务

支持Qdrant向量数据库的操作
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import uuid


@dataclass
class VectorRecord:
    """向量记录"""
    id: str
    vector: List[float]
    payload: Dict[str, any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """搜索结果"""
    id: str
    score: float
    payload: Dict[str, any]
    vector: Optional[List[float]] = None


class VectorStore:
    """向量存储服务"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "outeye_documents",
        vector_size: int = 1024,
        distance: str = "Cosine"
    ):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化Qdrant客户端"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            self.client = QdrantClient(host=self.host, port=self.port)

            # 检查集合是否存在，不存在则创建
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE if self.distance == "Cosine" else Distance.EUCLID
                    )
                )
                print(f"创建集合: {self.collection_name}")

        except ImportError:
            print("警告: qdrant_client未安装，将使用内存存储")
            self.client = None
            self._memory_store: Dict[str, VectorRecord] = {}

        except Exception as e:
            print(f"Qdrant连接失败: {e}，将使用内存存储")
            self.client = None
            self._memory_store: Dict[str, VectorRecord] = {}

    def upsert(self, records: List[VectorRecord]) -> bool:
        """
        插入或更新记录

        Args:
            records: 向量记录列表

        Returns:
            是否成功
        """
        if self.client is not None:
            return self._upsert_qdrant(records)
        else:
            return self._upsert_memory(records)

    def _upsert_qdrant(self, records: List[VectorRecord]) -> bool:
        """使用Qdrant插入记录"""
        try:
            from qdrant_client.models import PointStruct

            points = []
            for record in records:
                points.append(PointStruct(
                    id=record.id,
                    vector=record.vector,
                    payload=record.payload
                ))

            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

            return True

        except Exception as e:
            print(f"Qdrant插入失败: {e}")
            return False

    def _upsert_memory(self, records: List[VectorRecord]) -> bool:
        """使用内存存储"""
        for record in records:
            self._memory_store[record.id] = record
        return True

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_conditions: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0
    ) -> List[SearchResult]:
        """
        搜索相似向量

        Args:
            query_vector: 查询向量
            top_k: 返回数量
            filter_conditions: 过滤条件
            score_threshold: 分数阈值

        Returns:
            搜索结果列表
        """
        if self.client is not None:
            return self._search_qdrant(query_vector, top_k, filter_conditions, score_threshold)
        else:
            return self._search_memory(query_vector, top_k, filter_conditions, score_threshold)

    def _search_qdrant(
        self,
        query_vector: List[float],
        top_k: int,
        filter_conditions: Optional[Dict[str, Any]],
        score_threshold: float
    ) -> List[SearchResult]:
        """使用Qdrant搜索"""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # 构建过滤条件
            query_filter = None
            if filter_conditions:
                conditions = []
                for key, value in filter_conditions.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                query_filter = Filter(must=conditions)

            # 执行搜索
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter,
                score_threshold=score_threshold
            )

            # 转换结果
            search_results = []
            for result in results:
                search_results.append(SearchResult(
                    id=str(result.id),
                    score=result.score,
                    payload=result.payload or {}
                ))

            return search_results

        except Exception as e:
            print(f"Qdrant搜索失败: {e}")
            return []

    def _search_memory(
        self,
        query_vector: List[float],
        top_k: int,
        filter_conditions: Optional[Dict[str, Any]],
        score_threshold: float
    ) -> List[SearchResult]:
        """使用内存搜索"""
        import numpy as np

        query_vec = np.array(query_vector)
        results = []

        for record_id, record in self._memory_store.items():
            # 检查过滤条件
            if filter_conditions:
                match = True
                for key, value in filter_conditions.items():
                    if record.payload.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            # 计算相似度
            record_vec = np.array(record.vector)
            dot_product = np.dot(query_vec, record_vec)
            norm1 = np.linalg.norm(query_vec)
            norm2 = np.linalg.norm(record_vec)

            if norm1 == 0 or norm2 == 0:
                score = 0.0
            else:
                score = float(dot_product / (norm1 * norm2))

            # 检查分数阈值
            if score >= score_threshold:
                results.append(SearchResult(
                    id=record_id,
                    score=score,
                    payload=record.payload
                ))

        # 排序并返回top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def delete(self, ids: List[str]) -> bool:
        """
        删除记录

        Args:
            ids: 记录ID列表

        Returns:
            是否成功
        """
        if self.client is not None:
            return self._delete_qdrant(ids)
        else:
            return self._delete_memory(ids)

    def _delete_qdrant(self, ids: List[str]) -> bool:
        """使用Qdrant删除"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids
            )
            return True
        except Exception as e:
            print(f"Qdrant删除失败: {e}")
            return False

    def _delete_memory(self, ids: List[str]) -> bool:
        """使用内存删除"""
        for record_id in ids:
            if record_id in self._memory_store:
                del self._memory_store[record_id]
        return True

    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        if self.client is not None:
            return self._get_info_qdrant()
        else:
            return self._get_info_memory()

    def _get_info_qdrant(self) -> Dict[str, Any]:
        """获取Qdrant集合信息"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            print(f"获取集合信息失败: {e}")
            return {}

    def _get_info_memory(self) -> Dict[str, Any]:
        """获取内存存储信息"""
        return {
            "name": self.collection_name,
            "vectors_count": len(self._memory_store),
            "points_count": len(self._memory_store),
            "status": "memory"
        }

    def count(self) -> int:
        """获取记录数量"""
        if self.client is not None:
            try:
                info = self.client.get_collection(self.collection_name)
                return info.points_count
            except:
                return 0
        else:
            return len(self._memory_store)
