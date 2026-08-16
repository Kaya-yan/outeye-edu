"""
存储配额与磁盘监控测试（TDD）

目标：
1. 每用户 100MB 配额
2. 超配额时拒绝上传
3. 磁盘用量可监控
"""

import pytest
from sqlalchemy import select

from app.models.document import Document
from app.services.storage import (
    USER_QUOTA_BYTES,
    get_user_storage_used,
    check_user_quota,
    get_disk_usage,
)


class TestUserQuota:
    """用户配额测试"""

    @pytest.mark.asyncio
    async def test_quota_is_100mb(self):
        """每用户配额应为 100MB"""
        assert USER_QUOTA_BYTES == 100 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_get_user_storage_used_sums_file_sizes(self, test_db_session):
        """应统计用户所有文档的总大小"""
        test_db_session.add(Document(
            id="d1", user_id="user-1", title="a", file_size=1000, status="indexed"
        ))
        test_db_session.add(Document(
            id="d2", user_id="user-1", title="b", file_size=2000, status="indexed"
        ))
        test_db_session.add(Document(
            id="d3", user_id="user-2", title="c", file_size=5000, status="indexed"
        ))
        await test_db_session.commit()

        used = await get_user_storage_used(test_db_session, "user-1")
        assert used == 3000

    @pytest.mark.asyncio
    async def test_check_user_quota_under_limit(self, test_db_session):
        """未超配额时应允许上传"""
        test_db_session.add(Document(
            id="d1", user_id="user-1", title="a", file_size=1000, status="indexed"
        ))
        await test_db_session.commit()

        allowed = await check_user_quota(test_db_session, "user-1", new_size=1000)
        assert allowed is True

    @pytest.mark.asyncio
    async def test_check_user_quota_over_limit(self, test_db_session):
        """超配额时应拒绝上传"""
        test_db_session.add(Document(
            id="d1", user_id="user-1", title="a",
            file_size=USER_QUOTA_BYTES - 1, status="indexed"
        ))
        await test_db_session.commit()

        allowed = await check_user_quota(test_db_session, "user-1", new_size=1000)
        assert allowed is False


class TestDiskUsage:
    """磁盘监控测试"""

    def test_get_disk_usage_returns_stats(self, tmp_path):
        """磁盘用量应返回 total/used/free 统计"""
        stats = get_disk_usage(str(tmp_path))

        assert stats["total"] > 0
        assert stats["free"] >= 0
        assert "used" in stats
