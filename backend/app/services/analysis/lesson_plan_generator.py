"""
教案自动生成系统

基于分析结果生成个性化教案
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class LearningObjective:
    """学习目标"""
    description: str
    bloom_level: str
    measurable: bool
    assessment_method: str


@dataclass
class TeachingActivity:
    """教学活动"""
    name: str
    description: str
    duration: int  # 分钟
    activity_type: str  # presentation, practice, production, assessment
    materials: List[str]
    interaction_pattern: str  # individual, pair, group, whole_class


@dataclass
class LessonPlan:
    """教案"""
    title: str
    level: str
    duration: int  # 分钟
    objectives: List[LearningObjective]
    activities: List[TeachingActivity]
    materials: List[str]
    assessment: Dict[str, Any]
    differentiation: Dict[str, List[str]]
    homework: Optional[str]


class LessonPlanGenerator:
    """教案生成器"""

    def __init__(self):
        # Bloom分类学层级
        self.bloom_levels = [
            "remember", "understand", "apply", "analyze", "evaluate", "create"
        ]

        # 活动模板
        self.activity_templates = {
            "warm_up": {
                "name": "热身活动",
                "duration": 5,
                "type": "presentation",
                "interaction": "whole_class"
            },
            "lead_in": {
                "name": "导入",
                "duration": 5,
                "type": "presentation",
                "interaction": "whole_class"
            },
            "presentation": {
                "name": "知识呈现",
                "duration": 15,
                "type": "presentation",
                "interaction": "whole_class"
            },
            "practice": {
                "name": "练习活动",
                "duration": 15,
                "type": "practice",
                "interaction": "pair"
            },
            "production": {
                "name": "产出活动",
                "duration": 15,
                "type": "production",
                "interaction": "group"
            },
            "summary": {
                "name": "总结",
                "duration": 5,
                "type": "assessment",
                "interaction": "whole_class"
            }
        }

    def generate(
        self,
        text_analysis: Dict[str, Any],
        student_level: str = "B1",
        lesson_duration: int = 45,
        focus_skills: Optional[List[str]] = None
    ) -> LessonPlan:
        """
        生成教案

        Args:
            text_analysis: 课文分析结果
            student_level: 学生水平
            lesson_duration: 课时（分钟）
            focus_skills: 重点技能

        Returns:
            教案
        """
        # 生成学习目标
        objectives = self._generate_objectives(text_analysis, student_level, focus_skills)

        # 生成教学活动
        activities = self._generate_activities(
            text_analysis, student_level, lesson_duration, objectives
        )

        # 生成教学材料
        materials = self._generate_materials(text_analysis, activities)

        # 生成评估方式
        assessment = self._generate_assessment(objectives)

        # 生成差异化策略
        differentiation = self._generate_differentiation(student_level)

        # 生成作业
        homework = self._generate_homework(text_analysis, objectives)

        return LessonPlan(
            title=text_analysis.get("title", "课文教学"),
            level=student_level,
            duration=lesson_duration,
            objectives=objectives,
            activities=activities,
            materials=materials,
            assessment=assessment,
            differentiation=differentiation,
            homework=homework
        )

    def _generate_objectives(
        self,
        text_analysis: Dict[str, Any],
        student_level: str,
        focus_skills: Optional[List[str]]
    ) -> List[LearningObjective]:
        """生成学习目标"""
        objectives = []

        # 语言知识目标
        lexical = text_analysis.get("lexical", {})
        if lexical.get("academic_words"):
            objectives.append(LearningObjective(
                description=f"掌握{len(lexical['academic_words'][:5])}个学术词汇的含义和用法",
                bloom_level="understand",
                measurable=True,
                assessment_method="词汇测试"
            ))

        # 阅读理解目标
        objectives.append(LearningObjective(
            description="理解课文主旨和关键细节",
            bloom_level="understand",
            measurable=True,
            assessment_method="阅读理解题"
        ))

        # 批判性思维目标
        discourse = text_analysis.get("discourse", {})
        if discourse.get("genre_type") == "argumentative":
            objectives.append(LearningObjective(
                description="分析作者的论证结构和论据",
                bloom_level="analyze",
                measurable=True,
                assessment_method="论证分析"
            ))

        # 根据重点技能添加目标
        if focus_skills:
            if "writing" in focus_skills:
                objectives.append(LearningObjective(
                    description="模仿课文结构进行写作",
                    bloom_level="apply",
                    measurable=True,
                    assessment_method="写作任务"
                ))

            if "speaking" in focus_skills:
                objectives.append(LearningObjective(
                    description="就课文主题进行讨论和表达观点",
                    bloom_level="evaluate",
                    measurable=True,
                    assessment_method="口语展示"
                ))

        return objectives

    def _generate_activities(
        self,
        text_analysis: Dict[str, Any],
        student_level: str,
        lesson_duration: int,
        objectives: List[LearningObjective]
    ) -> List[TeachingActivity]:
        """生成教学活动"""
        activities = []

        # 计算时间分配
        if lesson_duration >= 45:
            warm_up_time = 5
            lead_in_time = 5
            presentation_time = 15
            practice_time = 10
            production_time = 5
            summary_time = 5
        else:
            warm_up_time = 3
            lead_in_time = 3
            presentation_time = 10
            practice_time = 7
            production_time = 3
            summary_time = 4

        # 热身活动
        activities.append(TeachingActivity(
            name="热身活动",
            description="通过提问或讨论激活学生已有知识",
            duration=warm_up_time,
            activity_type="presentation",
            materials=["白板", "PPT"],
            interaction_pattern="whole_class"
        ))

        # 导入
        activities.append(TeachingActivity(
            name="导入",
            description="引入课文主题，激发学习兴趣",
            duration=lead_in_time,
            activity_type="presentation",
            materials=["图片", "视频"],
            interaction_pattern="whole_class"
        ))

        # 预教词汇
        lexical = text_analysis.get("lexical", {})
        if lexical.get("unknown_words"):
            activities.append(TeachingActivity(
                name="词汇预教",
                description=f"预教{min(10, len(lexical['unknown_words']))}个关键词汇",
                duration=10,
                activity_type="presentation",
                materials=["词汇表", "例句"],
                interaction_pattern="whole_class"
            ))

        # 阅读理解
        activities.append(TeachingActivity(
            name="阅读理解",
            description="学生阅读课文，完成理解任务",
            duration=practice_time,
            activity_type="practice",
            materials=["课文", "阅读理解题"],
            interaction_pattern="individual"
        ))

        # 语篇分析
        discourse = text_analysis.get("discourse", {})
        if discourse.get("genre_type"):
            activities.append(TeachingActivity(
                name="语篇分析",
                description=f"分析{discourse['genre_type']}体裁的结构特点",
                duration=10,
                activity_type="practice",
                materials=["分析框架", "课文"],
                interaction_pattern="pair"
            ))

        # 讨论活动
        activities.append(TeachingActivity(
            name="小组讨论",
            description="就课文主题进行小组讨论",
            duration=production_time,
            activity_type="production",
            materials=["讨论问题"],
            interaction_pattern="group"
        ))

        # 总结
        activities.append(TeachingActivity(
            name="总结",
            description="总结学习内容，布置作业",
            duration=summary_time,
            activity_type="assessment",
            materials=[],
            interaction_pattern="whole_class"
        ))

        return activities

    def _generate_materials(
        self,
        text_analysis: Dict[str, Any],
        activities: List[TeachingActivity]
    ) -> List[str]:
        """生成教学材料"""
        materials = set()

        # 从活动中收集材料
        for activity in activities:
            materials.update(activity.materials)

        # 根据分析结果添加材料
        lexical = text_analysis.get("lexical", {})
        if lexical.get("unknown_words"):
            materials.add("词汇表")

        if lexical.get("academic_words"):
            materials.add("学术词汇表")

        discourse = text_analysis.get("discourse", {})
        if discourse.get("genre_type"):
            materials.add("体裁分析框架")

        return list(materials)

    def _generate_assessment(self, objectives: List[LearningObjective]) -> Dict[str, Any]:
        """生成评估方式"""
        assessment = {
            "formative": [],
            "summative": []
        }

        # 形成性评估
        assessment["formative"].append({
            "type": "课堂观察",
            "description": "观察学生参与度和理解程度"
        })

        assessment["formative"].append({
            "type": "提问",
            "description": "通过提问检查理解"
        })

        # 总结性评估
        for obj in objectives:
            if obj.measurable:
                assessment["summative"].append({
                    "type": obj.assessment_method,
                    "description": f"评估：{obj.description}"
                })

        return assessment

    def _generate_differentiation(self, student_level: str) -> Dict[str, List[str]]:
        """生成差异化策略"""
        differentiation = {
            "support": [],
            "extension": []
        }

        # 支持策略
        differentiation["support"].append("提供词汇表和例句")
        differentiation["support"].append("简化任务要求")
        differentiation["support"].append("提供额外的练习时间")
        differentiation["support"].append("使用视觉辅助")

        # 拓展策略
        differentiation["extension"].append("增加任务复杂度")
        differentiation["extension"].append("要求更深入的分析")
        differentiation["extension"].append("提供额外的阅读材料")
        differentiation["extension"].append("鼓励创造性表达")

        # 根据水平调整
        if student_level in ["A1", "A2"]:
            differentiation["support"].append("使用双语解释")
            differentiation["support"].append("提供更多的示范")

        return differentiation

    def _generate_homework(
        self,
        text_analysis: Dict[str, Any],
        objectives: List[LearningObjective]
    ) -> str:
        """生成作业"""
        homework_parts = []

        # 词汇作业
        lexical = text_analysis.get("lexical", {})
        if lexical.get("academic_words"):
            homework_parts.append(f"复习并掌握以下学术词汇：{', '.join(lexical['academic_words'][:5])}")

        # 阅读作业
        homework_parts.append("重读课文，完成课后练习")

        # 写作作业（如果有写作目标）
        for obj in objectives:
            if "写作" in obj.description:
                homework_parts.append("模仿课文结构，写一篇短文（150-200词）")
                break

        return "；".join(homework_parts)

    def format_lesson_plan(self, plan: LessonPlan) -> str:
        """格式化教案"""
        output = []
        output.append(f"# {plan.title} 教案")
        output.append(f"\n## 基本信息")
        output.append(f"- 水平：{plan.level}")
        output.append(f"- 时长：{plan.duration}分钟")

        output.append(f"\n## 学习目标")
        for i, obj in enumerate(plan.objectives, 1):
            output.append(f"{i}. {obj.description}（{obj.bloom_level}）")

        output.append(f"\n## 教学活动")
        for activity in plan.activities:
            output.append(f"\n### {activity.name}（{activity.duration}分钟）")
            output.append(f"- 描述：{activity.description}")
            output.append(f"- 互动形式：{activity.interaction_pattern}")
            if activity.materials:
                output.append(f"- 材料：{', '.join(activity.materials)}")

        output.append(f"\n## 教学材料")
        for material in plan.materials:
            output.append(f"- {material}")

        output.append(f"\n## 评估方式")
        output.append("### 形成性评估")
        for item in plan.assessment.get("formative", []):
            output.append(f"- {item['type']}: {item['description']}")
        output.append("### 总结性评估")
        for item in plan.assessment.get("summative", []):
            output.append(f"- {item['type']}: {item['description']}")

        output.append(f"\n## 差异化策略")
        output.append("### 支持策略")
        for strategy in plan.differentiation.get("support", []):
            output.append(f"- {strategy}")
        output.append("### 拓展策略")
        for strategy in plan.differentiation.get("extension", []):
            output.append(f"- {strategy}")

        if plan.homework:
            output.append(f"\n## 作业")
            output.append(plan.homework)

        return "\n".join(output)
