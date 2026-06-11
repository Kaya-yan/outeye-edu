"""
学情分析与评估系统

跟踪学习效果，评估学习能力，提供个性化建议
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LearningRecord:
    """学习记录"""
    student_id: str
    timestamp: str
    activity_type: str  # reading, writing, speaking, listening
    content_id: str
    score: float
    duration: int  # 分钟
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AbilityAssessment:
    """能力评估"""
    student_id: str
    assessment_date: str
    overall_level: str  # CEFR
    skill_levels: Dict[str, str]  # reading, writing, speaking, listening
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]


@dataclass
class LearningProgress:
    """学习进度"""
    student_id: str
    period: str  # daily, weekly, monthly
    total_time: int  # 分钟
    activities_count: int
    avg_score: float
    improvement_rate: float
    goal_achievement: float


class LearningAnalytics:
    """学情分析系统"""

    def __init__(self):
        # 学习记录存储（实际应使用数据库）
        self.records: Dict[str, List[LearningRecord]] = {}

        # 能力评估阈值
        self.level_thresholds = {
            "A1": 20,
            "A2": 35,
            "B1": 50,
            "B2": 65,
            "C1": 80,
            "C2": 95
        }

    def record_activity(self, record: LearningRecord):
        """
        记录学习活动

        Args:
            record: 学习记录
        """
        student_id = record.student_id
        if student_id not in self.records:
            self.records[student_id] = []

        self.records[student_id].append(record)

    def assess_ability(self, student_id: str) -> AbilityAssessment:
        """
        评估学习能力

        Args:
            student_id: 学生ID

        Returns:
            能力评估结果
        """
        records = self.records.get(student_id, [])

        if not records:
            return AbilityAssessment(
                student_id=student_id,
                assessment_date=datetime.now().isoformat(),
                overall_level="A1",
                skill_levels={
                    "reading": "A1",
                    "writing": "A1",
                    "speaking": "A1",
                    "listening": "A1"
                },
                strengths=[],
                weaknesses=["缺少学习数据"],
                recommendations=["建议开始学习活动"]
            )

        # 计算各技能得分
        skill_scores = self._calculate_skill_scores(records)

        # 确定各技能水平
        skill_levels = {}
        for skill, score in skill_scores.items():
            skill_levels[skill] = self._score_to_level(score)

        # 计算总体水平
        overall_score = sum(skill_scores.values()) / len(skill_scores)
        overall_level = self._score_to_level(overall_score)

        # 识别优势和弱点
        strengths = self._identify_strengths(skill_scores)
        weaknesses = self._identify_weaknesses(skill_scores)

        # 生成建议
        recommendations = self._generate_recommendations(
            skill_scores, strengths, weaknesses
        )

        return AbilityAssessment(
            student_id=student_id,
            assessment_date=datetime.now().isoformat(),
            overall_level=overall_level,
            skill_levels=skill_levels,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations
        )

    def _calculate_skill_scores(self, records: List[LearningRecord]) -> Dict[str, float]:
        """计算各技能得分"""
        skill_records = {
            "reading": [],
            "writing": [],
            "speaking": [],
            "listening": []
        }

        for record in records:
            if record.activity_type in skill_records:
                skill_records[record.activity_type].append(record.score)

        skill_scores = {}
        for skill, scores in skill_records.items():
            if scores:
                # 计算加权平均（最近的记录权重更高）
                weights = [i + 1 for i in range(len(scores))]
                weighted_sum = sum(s * w for s, w in zip(scores, weights))
                total_weight = sum(weights)
                skill_scores[skill] = weighted_sum / total_weight
            else:
                skill_scores[skill] = 0.0

        return skill_scores

    def _score_to_level(self, score: float) -> str:
        """将分数转换为水平"""
        for level, threshold in sorted(
            self.level_thresholds.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if score >= threshold:
                return level
        return "A1"

    def _identify_strengths(self, skill_scores: Dict[str, float]) -> List[str]:
        """识别优势"""
        if not skill_scores:
            return []

        avg_score = sum(skill_scores.values()) / len(skill_scores)
        strengths = []

        for skill, score in skill_scores.items():
            if score > avg_score + 10:
                strengths.append(skill)

        return strengths

    def _identify_weaknesses(self, skill_scores: Dict[str, float]) -> List[str]:
        """识别弱点"""
        if not skill_scores:
            return []

        avg_score = sum(skill_scores.values()) / len(skill_scores)
        weaknesses = []

        for skill, score in skill_scores.items():
            if score < avg_score - 10:
                weaknesses.append(skill)

        return weaknesses

    def _generate_recommendations(
        self,
        skill_scores: Dict[str, float],
        strengths: List[str],
        weaknesses: List[str]
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        # 基于弱点的建议
        skill_names = {
            "reading": "阅读",
            "writing": "写作",
            "speaking": "口语",
            "listening": "听力"
        }

        for weakness in weaknesses:
            skill_name = skill_names.get(weakness, weakness)
            recommendations.append(f"建议加强{skill_name}练习")

        # 基于整体水平的建议
        avg_score = sum(skill_scores.values()) / len(skill_scores)
        if avg_score < 30:
            recommendations.append("建议从基础开始，系统学习")
        elif avg_score < 50:
            recommendations.append("建议加强基础知识巩固")
        elif avg_score < 70:
            recommendations.append("建议增加实践练习")
        else:
            recommendations.append("建议挑战更高难度的内容")

        return recommendations

    def get_progress(
        self,
        student_id: str,
        period: str = "weekly"
    ) -> LearningProgress:
        """
        获取学习进度

        Args:
            student_id: 学生ID
            period: 时间段

        Returns:
            学习进度
        """
        records = self.records.get(student_id, [])

        # 筛选时间段内的记录
        filtered_records = self._filter_by_period(records, period)

        if not filtered_records:
            return LearningProgress(
                student_id=student_id,
                period=period,
                total_time=0,
                activities_count=0,
                avg_score=0.0,
                improvement_rate=0.0,
                goal_achievement=0.0
            )

        # 计算统计指标
        total_time = sum(r.duration for r in filtered_records)
        activities_count = len(filtered_records)
        avg_score = sum(r.score for r in filtered_records) / len(filtered_records)

        # 计算进步率
        improvement_rate = self._calculate_improvement_rate(filtered_records)

        # 计算目标达成度
        goal_achievement = self._calculate_goal_achievement(filtered_records)

        return LearningProgress(
            student_id=student_id,
            period=period,
            total_time=total_time,
            activities_count=activities_count,
            avg_score=round(avg_score, 1),
            improvement_rate=round(improvement_rate, 2),
            goal_achievement=round(goal_achievement, 2)
        )

    def _filter_by_period(
        self,
        records: List[LearningRecord],
        period: str
    ) -> List[LearningRecord]:
        """按时间段筛选记录"""
        from datetime import datetime, timedelta

        now = datetime.now()

        if period == "daily":
            start_time = now - timedelta(days=1)
        elif period == "weekly":
            start_time = now - timedelta(weeks=1)
        elif period == "monthly":
            start_time = now - timedelta(days=30)
        else:
            return records

        filtered = []
        for record in records:
            try:
                record_time = datetime.fromisoformat(record.timestamp)
                if record_time >= start_time:
                    filtered.append(record)
            except Exception:
                continue

        return filtered

    def _calculate_improvement_rate(self, records: List[LearningRecord]) -> float:
        """计算进步率"""
        if len(records) < 2:
            return 0.0

        # 按时间排序
        sorted_records = sorted(records, key=lambda r: r.timestamp)

        # 计算前半部分和后半部分的平均分
        mid = len(sorted_records) // 2
        first_half = sorted_records[:mid]
        second_half = sorted_records[mid:]

        if not first_half or not second_half:
            return 0.0

        avg_first = sum(r.score for r in first_half) / len(first_half)
        avg_second = sum(r.score for r in second_half) / len(second_half)

        if avg_first == 0:
            return 0.0

        improvement = (avg_second - avg_first) / avg_first
        return improvement

    def _calculate_goal_achievement(self, records: List[LearningRecord]) -> float:
        """计算目标达成度"""
        # 简化：基于分数达标率
        target_score = 70  # 目标分数

        achieved_count = sum(1 for r in records if r.score >= target_score)
        achievement_rate = achieved_count / len(records) if records else 0

        return achievement_rate

    def generate_report(self, student_id: str) -> Dict[str, Any]:
        """
        生成学习报告

        Args:
            student_id: 学生ID

        Returns:
            学习报告
        """
        # 能力评估
        ability = self.assess_ability(student_id)

        # 学习进度
        weekly_progress = self.get_progress(student_id, "weekly")
        monthly_progress = self.get_progress(student_id, "monthly")

        # 生成报告
        report = {
            "student_id": student_id,
            "report_date": datetime.now().isoformat(),
            "ability_assessment": {
                "overall_level": ability.overall_level,
                "skill_levels": ability.skill_levels,
                "strengths": ability.strengths,
                "weaknesses": ability.weaknesses
            },
            "learning_progress": {
                "weekly": {
                    "total_time": weekly_progress.total_time,
                    "activities_count": weekly_progress.activities_count,
                    "avg_score": weekly_progress.avg_score,
                    "improvement_rate": weekly_progress.improvement_rate
                },
                "monthly": {
                    "total_time": monthly_progress.total_time,
                    "activities_count": monthly_progress.activities_count,
                    "avg_score": monthly_progress.avg_score,
                    "improvement_rate": monthly_progress.improvement_rate
                }
            },
            "recommendations": ability.recommendations
        }

        return report
