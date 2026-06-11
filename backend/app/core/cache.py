"""
缓存模块 - 使用 Redis 缓存分析结果
"""

import json
import hashlib
from typing import Optional, Any
from loguru import logger

from app.core.config import settings


class CacheService:
    """缓存服务"""

    def __init__(self):
        self._redis = None
        self._prefix = "outeye:"
        self._default_ttl = 3600  # 1小时

    def _get_redis(self):
        """获取 Redis 连接"""
        if self._redis is None:
            try:
                import redis
                self._redis = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True
                )
                # 测试连接
                self._redis.ping()
                logger.info("Redis 连接成功")
            except Exception as e:
                logger.warning(f"Redis 连接失败，将禁用缓存: {e}")
                self._redis = None
        return self._redis

    def _make_key(self, namespace: str, key: str) -> str:
        """生成缓存键"""
        # 对长 key 进行哈希
        if len(key) > 100:
            key = hashlib.md5(key.encode()).hexdigest()
        return f"{self._prefix}{namespace}:{key}"

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """获取缓存"""
        redis = self._get_redis()
        if redis is None:
            return None

        try:
            cache_key = self._make_key(namespace, key)
            value = redis.get(cache_key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"缓存读取失败: {e}")
            return None

    def set(self, namespace: str, key: str, value: Any, ttl: int = None) -> bool:
        """设置缓存"""
        redis = self._get_redis()
        if redis is None:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            ttl = ttl or self._default_ttl
            redis.setex(cache_key, ttl, json.dumps(value, ensure_ascii=False))
            return True
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")
            return False

    def delete(self, namespace: str, key: str) -> bool:
        """删除缓存"""
        redis = self._get_redis()
        if redis is None:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            redis.delete(cache_key)
            return True
        except Exception as e:
            logger.warning(f"缓存删除失败: {e}")
            return False

    def clear_namespace(self, namespace: str) -> bool:
        """清除命名空间下的所有缓存"""
        redis = self._get_redis()
        if redis is None:
            return False

        try:
            pattern = f"{self._prefix}{namespace}:*"
            keys = redis.keys(pattern)
            if keys:
                redis.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"缓存清除失败: {e}")
            return False


# 全局缓存实例
cache = CacheService()
