"""
数据清理服务

定期清理过期数据，保持数据库容量在免费额度内
"""

from datetime import datetime, timedelta
from sqlalchemy import delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import AsyncSessionLocal
from app.models.learning import LearningRecord, UserBehavior
from app.models.analysis import AnalysisRecord


# 数据保留策略
RETENTION_POLICIES = {
    "user_behaviors": 30,  # 用户行为保留 30 天
    "learning_records": 90,  # 学习记录保留 90 天
    "analysis_records": 180,  # 分析记录保留 180 天
}


class DataCleanupService:
    """数据清理服务"""

    def __init__(self):
        self.policies = RETENTION_POLICIES

    async def cleanup_all(self):
        """执行所有清理任务"""
        logger.info("开始数据清理任务...")

        results = {}

        # 清理用户行为
        results["user_behaviors"] = await self.cleanup_user_behaviors()

        # 清理学习记录
        results["learning_records"] = await self.cleanup_learning_records()

        # 清理旧的分析记录（保留摘要）
        results["analysis_records"] = await self.cleanup_old_analysis_records()

        logger.info(f"数据清理完成: {results}")
        return results

    async def cleanup_user_behaviors(self) -> int:
        """清理过期的用户行为数据"""
        days = self.policies["user_behaviors"]
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        async with AsyncSessionLocal() as session:
            try:
                # 删除过期记录
                result = await session.execute(
                    delete(UserBehavior).where(
                        UserBehavior.created_at < cutoff_date
                    )
                )
                await session.commit()
                deleted_count = result.rowcount
                logger.info(f"清理用户行为记录: {deleted_count} 条（超过 {days} 天）")
                return deleted_count
            except Exception as e:
                await session.rollback()
                logger.error(f"清理用户行为记录失败: {e}")
                return 0

    async def cleanup_learning_records(self) -> int:
        """清理过期的学习记录"""
        days = self.policies["learning_records"]
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    delete(LearningRecord).where(
                        LearningRecord.created_at < cutoff_date
                    )
                )
                await session.commit()
                deleted_count = result.rowcount
                logger.info(f"清理学习记录: {deleted_count} 条（超过 {days} 天）")
                return deleted_count
            except Exception as e:
                await session.rollback()
                logger.error(f"清理学习记录失败: {e}")
                return 0

    async def cleanup_old_analysis_records(self) -> int:
        """清理旧的分析记录（保留最近的详细记录）"""
        days = self.policies["analysis_records"]
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        async with AsyncSessionLocal() as session:
            try:
                # 只删除详细结果，保留摘要
                result = await session.execute(
                    delete(AnalysisRecord).where(
                        AnalysisRecord.created_at < cutoff_date
                    )
                )
                await session.commit()
                deleted_count = result.rowcount
                logger.info(f"清理分析记录: {deleted_count} 条（超过 {days} 天）")
                return deleted_count
            except Exception as e:
                await session.rollback()
                logger.error(f"清理分析记录失败: {e}")
                return 0

    async def get_database_stats(self) -> dict:
        """获取数据库统计信息"""
        async with AsyncSessionLocal() as session:
            try:
                from sqlalchemy import func, select

                # 统计各表记录数
                stats = {}

                # 用户行为
                result = await session.execute(
                    select(func.count(UserBehavior.id))
                )
                stats["user_behaviors"] = result.scalar() or 0

                # 学习记录
                result = await session.execute(
                    select(func.count(LearningRecord.id))
                )
                stats["learning_records"] = result.scalar() or 0

                # 分析记录
                result = await session.execute(
                    select(func.count(AnalysisRecord.id))
                )
                stats["analysis_records"] = result.scalar() or 0

                return stats
            except Exception as e:
                logger.error(f"获取数据库统计失败: {e}")
                return {}


# 全局实例
data_cleanup_service = DataCleanupService()
