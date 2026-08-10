"""Seed official teaching component definitions on first startup."""

import uuid
from typing import List, Dict, Any

OFFICIAL_COMPONENTS: List[Dict[str, Any]] = [
    # ---- 课程导入 ----
    {
        "name": "课程封面页", "slug": "course-cover", "scope": "official",
        "summary": "课程标题、课文标题、教师信息与学习目标概览，适合课堂开场第一页",
        "category": "课程导入", "teaching_stage": "导入", "mode_support": "both",
        "subject_tags": ["通用", "开场"], "interaction_level": "static",
        "render_template_html": '<section class="cover-page" style="display:flex;align-items:center;justify-content:center;min-height:100vh;background:linear-gradient(135deg,#1e3a5f 0%,#3d5f9a 100%);color:#fff;padding:40px;text-align:center;font-family:system-ui,sans-serif"><div><h1 style="font-size:48px;margin:0 0 16px;font-weight:800">课程标题</h1><p style="font-size:20px;opacity:0.85;margin:0 0 8px">课文标题</p><p style="font-size:14px;opacity:0.6">授课教师 · 日期</p></div></section>',
    },
    {
        "name": "问题导入卡", "slug": "question-intro", "scope": "official",
        "summary": "开场引导问题，激活学生已有知识，适合课前热身与预测活动",
        "category": "课程导入", "teaching_stage": "导入", "mode_support": "both",
        "subject_tags": ["通用", "导入"], "interaction_level": "reveal",
        "render_template_html": '<div class="question-intro" style="padding:60px 40px;text-align:center;font-family:system-ui,sans-serif"><div style="font-size:28px;font-weight:700;color:#1e3a5f;margin-bottom:24px">思考题</div><p style="font-size:18px;color:#4b5563;max-width:600px;margin:0 auto;line-height:1.8">在此处输入引导问题...</p><div style="margin-top:32px"><button onclick="this.nextElementSibling.style.display=\'block\';this.style.display=\'none\'" style="padding:10px 32px;background:#3d5f9a;color:#fff;border:none;border-radius:8px;font-size:14px;cursor:pointer">点击揭晓提示</button><div style="display:none;margin-top:16px;padding:16px;background:#eef3f9;border-radius:8px;color:#2f4b7d;font-size:14px">提示/答案区域</div></div></div>',
    },
    {
        "name": "学习目标页", "slug": "learning-goals", "scope": "official",
        "summary": "明确告知学生本节课的知识、能力与思维目标",
        "category": "课程导入", "teaching_stage": "导入", "mode_support": "both",
        "subject_tags": ["通用", "目标"], "interaction_level": "static",
        "render_template_html": '<div style="padding:60px 40px;font-family:system-ui,sans-serif"><h2 style="font-size:28px;color:#1e3a5f;margin-bottom:32px;text-align:center">学习目标</h2><div style="max-width:700px;margin:0 auto;display:flex;flex-direction:column;gap:16px"><div style="padding:16px 20px;background:#eef3f9;border-left:4px solid #3d5f9a;border-radius:4px"><strong>知识目标</strong><p style="margin:8px 0 0;color:#4b5563">在此输入...</p></div><div style="padding:16px 20px;background:#fef3c7;border-left:4px solid #f59e0b;border-radius:4px"><strong>能力目标</strong><p style="margin:8px 0 0;color:#4b5563">在此输入...</p></div><div style="padding:16px 20px;background:#ecfdf5;border-left:4px solid #10b981;border-radius:4px"><strong>思维目标</strong><p style="margin:8px 0 0;color:#4b5563">在此输入...</p></div></div></div>',
    },
    # ---- 知识讲授 ----
    {
        "name": "词汇讲解卡", "slug": "vocab-card", "scope": "official",
        "summary": "展示单词、释义、例句与搭配，适合词汇教学环节",
        "category": "知识讲授", "teaching_stage": "讲授", "mode_support": "both",
        "subject_tags": ["词汇教学"], "interaction_level": "reveal",
        "render_template_html": '<div class="vocab-card" style="padding:40px;max-width:700px;margin:0 auto;font-family:system-ui,sans-serif"><div style="text-align:center;margin-bottom:24px"><span style="font-size:36px;font-weight:700;color:#1e3a5f">vocabulary</span><span style="margin-left:12px;font-size:16px;color:#6b7280">/vəˈkæbjəleri/</span></div><div style="background:#f9fafb;border-radius:12px;padding:24px"><p style="color:#374151;font-size:16px;line-height:1.6;margin:0 0 12px"><strong>释义：</strong>在此输入中文释义</p><p style="color:#374151;font-size:16px;line-height:1.6;margin:0 0 12px"><strong>例句：</strong><em>在此输入例句...</em></p><p style="color:#6b7280;font-size:14px;margin:0"><strong>搭配：</strong>在此输入常用搭配</p></div></div>',
    },
    {
        "name": "长难句拆解卡", "slug": "sentence-breakdown", "scope": "official",
        "summary": "逐步分解复杂句子的语法结构，适合语法教学与精读课",
        "category": "知识讲授", "teaching_stage": "讲授", "mode_support": "slides",
        "subject_tags": ["语法教学", "阅读理解"], "interaction_level": "reveal",
        "render_template_html": '<div style="padding:40px;font-family:system-ui,sans-serif;max-width:800px;margin:0 auto"><div style="background:#f9fafb;border-radius:12px;padding:28px;margin-bottom:20px;font-size:18px;line-height:1.8;color:#1f2937">在此粘贴原句...</div><div style="display:flex;flex-direction:column;gap:12px"><div style="padding:14px 18px;background:#eef3f9;border-radius:8px;font-size:14px;color:#2f4b7d"><strong>主语：</strong>点击展开</div><div style="padding:14px 18px;background:#fef3c7;border-radius:8px;font-size:14px;color:#92400e"><strong>谓语：</strong>点击展开</div><div style="padding:14px 18px;background:#ecfdf5;border-radius:8px;font-size:14px;color:#065f46"><strong>从句类型：</strong>点击展开</div></div></div>',
    },
    {
        "name": "理论依据卡", "slug": "theory-card", "scope": "official",
        "summary": "展示教学决策背后的语言学理论支撑，适合平台特色展示",
        "category": "知识讲授", "teaching_stage": "讲授", "mode_support": "both",
        "subject_tags": ["理论展示", "学术"], "interaction_level": "static",
        "render_template_html": '<div style="padding:32px;font-family:system-ui,sans-serif;max-width:700px;margin:0 auto"><div style="background:linear-gradient(135deg,#eef3f9,#d5e0ef);border-radius:12px;padding:24px"><div style="font-size:12px;color:#5b7ab3;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">理论依据</div><h3 style="font-size:18px;color:#1e3a5f;margin:0 0 12px">在此输入理论名称</h3><p style="font-size:14px;color:#374151;line-height:1.7;margin:0 0 12px">在此说明该理论如何支撑此教学决策...</p><div style="font-size:12px;color:#829cc9">来源：OutEye Wiki</div></div></div>',
    },
    # ---- 活动组织 ----
    {
        "name": "小组讨论任务卡", "slug": "group-discussion", "scope": "official",
        "summary": "结构化展示小组讨论的主题、分工与输出要求",
        "category": "活动组织", "teaching_stage": "活动", "mode_support": "both",
        "subject_tags": ["小组讨论", "合作学习"], "interaction_level": "timed",
        "render_template_html": '<div style="padding:40px;font-family:system-ui,sans-serif;max-width:700px;margin:0 auto"><h3 style="font-size:22px;color:#1e3a5f;margin:0 0 24px">小组讨论</h3><div style="display:grid;grid-template-columns:1fr 1fr;gap:16px"><div style="background:#f9fafb;border-radius:10px;padding:20px"><div style="font-size:13px;color:#6b7280;margin-bottom:8px">讨论主题</div><div style="font-size:16px;color:#1f2937;font-weight:600">在此输入主题</div></div><div style="background:#f9fafb;border-radius:10px;padding:20px"><div style="font-size:13px;color:#6b7280;margin-bottom:8px">时间</div><div style="font-size:32px;font-weight:700;color:#3d5f9a">5:00</div></div><div style="background:#f9fafb;border-radius:10px;padding:20px"><div style="font-size:13px;color:#6b7280;margin-bottom:8px">分工</div><div style="font-size:14px;color:#374151">记录员 · 发言人 · 计时员</div></div><div style="background:#f9fafb;border-radius:10px;padding:20px"><div style="font-size:13px;color:#6b7280;margin-bottom:8px">输出</div><div style="font-size:14px;color:#374151">口头汇报 / 海报 / 小组总结</div></div></div></div>',
    },
    {
        "name": "任务流程卡", "slug": "task-flow", "scope": "official",
        "summary": "分步骤展示课堂任务的流程，适合活动指导与项目式学习",
        "category": "活动组织", "teaching_stage": "活动", "mode_support": "both",
        "subject_tags": ["任务型教学", "流程"], "interaction_level": "reveal",
        "render_template_html": '<div style="padding:40px;font-family:system-ui,sans-serif;max-width:700px;margin:0 auto"><h3 style="font-size:22px;color:#1e3a5f;margin:0 0 32px;text-align:center">课堂任务</h3><div style="display:flex;flex-direction:column;gap:0"><div style="display:flex;align-items:flex-start;gap:16px;padding:0 0 28px"><div style="width:40px;height:40px;border-radius:50%;background:#3d5f9a;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:16px;flex-shrink:0">1</div><div><div style="font-weight:600;font-size:16px;color:#1f2937">第一步</div><p style="font-size:14px;color:#6b7280;margin:6px 0 0">任务说明...</p></div></div><div style="display:flex;align-items:flex-start;gap:16px;padding:0 0 28px"><div style="width:40px;height:40px;border-radius:50%;background:#3d5f9a;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:16px;flex-shrink:0">2</div><div><div style="font-weight:600;font-size:16px;color:#1f2937">第二步</div><p style="font-size:14px;color:#6b7280;margin:6px 0 0">任务说明...</p></div></div><div style="display:flex;align-items:flex-start;gap:16px"><div style="width:40px;height:40px;border-radius:50%;background:#3d5f9a;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:16px;flex-shrink:0">3</div><div><div style="font-weight:600;font-size:16px;color:#1f2937">第三步</div><p style="font-size:14px;color:#6b7280;margin:6px 0 0">任务说明...</p></div></div></div></div>',
    },
    # ---- 检测反馈 ----
    {
        "name": "单选题展示块", "slug": "quiz-choice", "scope": "official",
        "summary": "课堂单选题，支持点击选项后揭晓正确答案",
        "category": "检测反馈", "teaching_stage": "检测", "mode_support": "both",
        "subject_tags": ["课堂检测", "选择题"], "interaction_level": "local_interactive",
        "render_template_html": '<div style="padding:40px;font-family:system-ui,sans-serif;max-width:700px;margin:0 auto"><h3 style="font-size:20px;color:#1e3a5f;margin:0 0 24px">课堂检测</h3><p style="font-size:16px;color:#374151;margin:0 0 24px">题干内容...</p><div style="display:flex;flex-direction:column;gap:10px"><div onclick="this.style.background=this.dataset.correct?\'#ecfdf5\':\'#fef2f2\';this.style.borderColor=this.dataset.correct?\'#10b981\':\'#ef4444\'" data-correct="false" style="padding:14px 18px;border:2px solid #e5e7eb;border-radius:10px;cursor:pointer;font-size:15px;transition:all 0.2s">A. 选项一</div><div onclick="this.style.background=this.dataset.correct?\'#ecfdf5\':\'#fef2f2\';this.style.borderColor=this.dataset.correct?\'#10b981\':\'#ef4444\'" data-correct="true" style="padding:14px 18px;border:2px solid #e5e7eb;border-radius:10px;cursor:pointer;font-size:15px;transition:all 0.2s">B. 选项二（正确）</div><div onclick="this.style.background=this.dataset.correct?\'#ecfdf5\':\'#fef2f2\';this.style.borderColor=this.dataset.correct?\'#10b981\':\'#ef4444\'" data-correct="false" style="padding:14px 18px;border:2px solid #e5e7eb;border-radius:10px;cursor:pointer;font-size:15px;transition:all 0.2s">C. 选项三</div></div></div>',
    },
    {
        "name": "点击揭晓答案", "slug": "reveal-answer", "scope": "official",
        "summary": "教师提问后点击揭晓答案，适合课堂问答与检查活动",
        "category": "检测反馈", "teaching_stage": "检测", "mode_support": "both",
        "subject_tags": ["课堂检测", "问答"], "interaction_level": "reveal",
        "render_template_html": '<div style="padding:50px 40px;text-align:center;font-family:system-ui,sans-serif"><div style="font-size:22px;font-weight:600;color:#1e3a5f;margin-bottom:32px">问题内容...</div><button onclick="this.nextElementSibling.style.display=\'block\';this.style.display=\'none\'" style="padding:12px 36px;background:#3d5f9a;color:#fff;border:none;border-radius:10px;font-size:16px;cursor:pointer">揭晓答案</button><div style="display:none;margin-top:24px;padding:24px;background:#ecfdf5;border:2px solid #10b981;border-radius:12px;font-size:18px;color:#065f46;font-weight:600">答案内容</div></div>',
    },
    {
        "name": "倒计时练习块", "slug": "timer-block", "scope": "official",
        "summary": "限时练习或讨论的倒计时组件，适合课堂限时活动",
        "category": "检测反馈", "teaching_stage": "检测", "mode_support": "both",
        "subject_tags": ["限时练习", "计时"], "interaction_level": "timed",
        "render_template_html": '<div style="padding:50px 40px;text-align:center;font-family:system-ui,sans-serif"><div style="font-size:18px;color:#6b7280;margin-bottom:16px">限时练习</div><div style="font-size:72px;font-weight:800;color:#1e3a5f;font-variant-numeric:tabular-nums" id="timer-display">3:00</div><p style="font-size:14px;color:#9ca3af;margin-top:12px">点击上方数字开始/暂停</p><script>var t=180,s=null,e=document.getElementById("timer-display");if(e){e.onclick=function(){if(s){clearInterval(s);s=null;return}s=setInterval(function(){if(t<=0){clearInterval(s);s=null;e.style.color="#ef4444";return}t--;var m=Math.floor(t/60),sec=t%60;e.textContent=m+":"+sec.toString().padStart(2,"0");if(t<=30)e.style.color="#f59e0b"},1000)}}</script></div>',
    },
    # ---- 总结反思 ----
    {
        "name": "本课总结页", "slug": "summary-page", "scope": "official",
        "summary": "结构化回顾本节课重点内容，适合课堂收束环节",
        "category": "总结反思", "teaching_stage": "总结", "mode_support": "both",
        "subject_tags": ["课堂总结", "复习"], "interaction_level": "static",
        "render_template_html": '<div style="padding:50px 40px;font-family:system-ui,sans-serif;max-width:800px;margin:0 auto"><h2 style="font-size:28px;color:#1e3a5f;text-align:center;margin:0 0 36px">本课总结</h2><div style="display:grid;grid-template-columns:1fr 1fr;gap:16px"><div style="background:#eef3f9;border-radius:10px;padding:20px"><div style="font-weight:600;font-size:15px;color:#2f4b7d;margin-bottom:8px">核心词汇</div><p style="font-size:14px;color:#374151;margin:0">在此输入...</p></div><div style="background:#fef3c7;border-radius:10px;padding:20px"><div style="font-weight:600;font-size:15px;color:#92400e;margin-bottom:8px">重点语法</div><p style="font-size:14px;color:#374151;margin:0">在此输入...</p></div><div style="background:#ecfdf5;border-radius:10px;padding:20px"><div style="font-weight:600;font-size:15px;color:#065f46;margin-bottom:8px">阅读策略</div><p style="font-size:14px;color:#374151;margin:0">在此输入...</p></div><div style="background:#f3e8ff;border-radius:10px;padding:20px"><div style="font-weight:600;font-size:15px;color:#6b21a8;margin-bottom:8px">文化要点</div><p style="font-size:14px;color:#374151;margin:0">在此输入...</p></div></div></div>',
    },
    {
        "name": "Takeaways 总结卡", "slug": "takeaways", "scope": "official",
        "summary": "用 3-5 条要点帮助学生回忆本节课最重要的收获",
        "category": "总结反思", "teaching_stage": "总结", "mode_support": "both",
        "subject_tags": ["课堂总结", "要点"], "interaction_level": "static",
        "render_template_html": '<div style="padding:50px 40px;font-family:system-ui,sans-serif;max-width:700px;margin:0 auto"><h3 style="font-size:22px;color:#1e3a5f;text-align:center;margin:0 0 32px">Takeaways</h3><div style="display:flex;flex-direction:column;gap:14px"><div style="display:flex;align-items:center;gap:14px;padding:14px 18px;background:#f9fafb;border-radius:10px"><span style="font-size:20px">1</span><span style="font-size:15px;color:#374151">要点一...</span></div><div style="display:flex;align-items:center;gap:14px;padding:14px 18px;background:#f9fafb;border-radius:10px"><span style="font-size:20px">2</span><span style="font-size:15px;color:#374151">要点二...</span></div><div style="display:flex;align-items:center;gap:14px;padding:14px 18px;background:#f9fafb;border-radius:10px"><span style="font-size:20px">3</span><span style="font-size:15px;color:#374151">要点三...</span></div></div></div>',
    },
    # ---- 作业延伸 ----
    {
        "name": "作业布置页", "slug": "homework", "scope": "official",
        "summary": "清晰展示课后任务、提交要求与评分提示",
        "category": "作业延伸", "teaching_stage": "作业", "mode_support": "both",
        "subject_tags": ["课后作业", "任务"], "interaction_level": "static",
        "render_template_html": '<div style="padding:40px;font-family:system-ui,sans-serif;max-width:700px;margin:0 auto"><h3 style="font-size:22px;color:#1e3a5f;margin:0 0 24px">课后任务</h3><div style="background:#f9fafb;border-radius:12px;padding:24px;margin-bottom:16px"><div style="font-weight:600;font-size:15px;color:#1f2937;margin-bottom:8px">必做</div><p style="font-size:14px;color:#6b7280;margin:0;line-height:1.7">任务说明...</p></div><div style="background:#f9fafb;border-radius:12px;padding:24px;margin-bottom:16px"><div style="font-weight:600;font-size:15px;color:#1f2937;margin-bottom:8px">选做</div><p style="font-size:14px;color:#6b7280;margin:0;line-height:1.7">任务说明...</p></div><div style="padding:12px 16px;background:#eef3f9;border-radius:8px;font-size:12px;color:#5b7ab3">提交截止：<strong>在此输入日期</strong> · 提交方式：在此输入</div></div>',
    },
    # ---- 教师辅助 ----
    {
        "name": "教师备注块", "slug": "teacher-notes", "scope": "official",
        "summary": "仅在教师端显示的备注提醒，展示时可通过 N 键切换显示",
        "category": "教师辅助", "teaching_stage": "辅助", "mode_support": "both",
        "subject_tags": ["教师"], "interaction_level": "static",
        "render_template_html": '<div class="teacher-note" style="padding:16px;background:#fef3c7;border-left:4px solid #f59e0b;border-radius:4px;font-size:13px;color:#92400e;margin:16px;font-family:system-ui,sans-serif"><strong>教师备注：</strong>在此输入...</div>',
    },
]

_OFFICIAL_SLUGS = {c["slug"] for c in OFFICIAL_COMPONENTS}


def seed_official_components_via_connection(conn):
    """Seed official components using a sync SQLAlchemy connection. Safe to call from async.run_sync()."""
    from sqlalchemy.orm import Session
    from app.models.courseware import ComponentDefinition

    session = Session(bind=conn)
    try:
        existing = session.query(ComponentDefinition).filter(
            ComponentDefinition.scope == "official"
        ).count()
        if existing >= len(OFFICIAL_COMPONENTS):
            return

        for comp in OFFICIAL_COMPONENTS:
            exists = session.query(ComponentDefinition).filter(
                ComponentDefinition.slug == comp["slug"],
                ComponentDefinition.scope == "official",
            ).first()
            if exists:
                continue
            c = ComponentDefinition(
                id=str(uuid.uuid4()),
                owner_user_id=None,
                **comp,
                community_status="approved",
                is_publishable=False,
            )
            session.add(c)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[courseware_seed] Could not seed: {e}")
    finally:
        session.close()
