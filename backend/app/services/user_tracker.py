"""
用户行为追踪服务
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import AsyncSessionLocal
from app.models.learning import UserBehavior


class UserTracker:
    """用户行为追踪器"""

    async def track_event(
        self,
        event_type: str,
        event_name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        page_url: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        追踪用户事件

        Args:
            event_type: 事件类型（page_view, click, api_call, error）
            event_name: 事件名称
            user_id: 用户ID
            session_id: 会话ID
            page_url: 页面URL
            event_data: 事件数据
            duration: 耗时（毫秒）
            success: 是否成功
            error_message: 错误信息
            user_agent: 浏览器信息
            ip_address: IP地址
        """
        try:
            # 检测设备类型
            device_type = self._detect_device_type(user_agent)

            async with AsyncSessionLocal() as session:
                behavior = UserBehavior(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    session_id=session_id,
                    event_type=event_type,
                    event_name=event_name,
                    page_url=page_url,
                    event_data=event_data,
                    duration=duration,
                    success=success,
                    error_message=error_message,
                    user_agent=user_agent,
                    ip_address=ip_address,
                    device_type=device_type,
                    created_at=datetime.utcnow()
                )
                session.add(behavior)
                await session.commit()

        except Exception as e:
            logger.warning(f"用户行为追踪失败: {e}")

    async def track_page_view(
        self,
        page_url: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        duration: Optional[float] = None
    ):
        """追踪页面访问"""
        await self.track_event(
            event_type="page_view",
            event_name=f"visit_{page_url}",
            user_id=user_id,
            session_id=session_id,
            page_url=page_url,
            duration=duration
        )

    async def track_api_call(
        self,
        endpoint: str,
        method: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        duration: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """追踪 API 调用"""
        await self.track_event(
            event_type="api_call",
            event_name=f"{method}_{endpoint}",
            user_id=user_id,
            session_id=session_id,
            page_url=endpoint,
            event_data={"method": method},
            duration=duration,
            success=success,
            error_message=error_message
        )

    async def track_analysis(
        self,
        user_id: str,
        text_title: str,
        student_level: str,
        duration: float,
        success: bool = True
    ):
        """追踪课文分析事件"""
        await self.track_event(
            event_type="feature_use",
            event_name="text_analysis",
            user_id=user_id,
            event_data={
                "text_title": text_title,
                "student_level": student_level
            },
            duration=duration,
            success=success
        )

    async def track_lesson_plan_generation(
        self,
        user_id: str,
        student_level: str,
        duration: float,
        success: bool = True
    ):
        """追踪教案生成事件"""
        await self.track_event(
            event_type="feature_use",
            event_name="lesson_plan_generation",
            user_id=user_id,
            event_data={
                "student_level": student_level
            },
            duration=duration,
            success=success
        )

    def _detect_device_type(self, user_agent: Optional[str]) -> str:
        """检测设备类型"""
        if not user_agent:
            return "unknown"

        user_agent_lower = user_agent.lower()

        if any(m in user_agent_lower for m in ["mobile", "android", "iphone", "ipod"]):
            return "mobile"
        elif any(m in user_agent_lower for m in ["tablet", "ipad"]):
            return "tablet"
        else:
            return "desktop"

    async def get_user_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """获取用户统计数据"""
        try:
            from sqlalchemy import func, select, and_
            from datetime import timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=days)

            async with AsyncSessionLocal() as session:
                # 总访问次数
                result = await session.execute(
                    select(func.count(UserBehavior.id)).where(
                        and_(
                            UserBehavior.user_id == user_id,
                            UserBehavior.event_type == "page_view",
                            UserBehavior.created_at >= cutoff_date
                        )
                    )
                )
                total_visits = result.scalar() or 0

                # 功能使用次数
                result = await session.execute(
                    select(func.count(UserBehavior.id)).where(
                        and_(
                            UserBehavior.user_id == user_id,
                            UserBehavior.event_type == "feature_use",
                            UserBehavior.created_at >= cutoff_date
                        )
                    )
                )
                feature_usage = result.scalar() or 0

                # 平均会话时长
                result = await session.execute(
                    select(func.avg(UserBehavior.duration)).where(
                        and_(
                            UserBehavior.user_id == user_id,
                            UserBehavior.duration.isnot(None),
                            UserBehavior.created_at >= cutoff_date
                        )
                    )
                )
                avg_duration = result.scalar() or 0

                return {
                    "total_visits": total_visits,
                    "feature_usage": feature_usage,
                    "avg_session_duration": round(avg_duration, 2),
                    "period_days": days
                }

        except Exception as e:
            logger.error(f"获取用户统计失败: {e}")
            return {}


# 全局实例
user_tracker = UserTracker()
