window.elementFactory = {
  templates: {
    'course-cover': '<section class="cover-page" style="display:flex;align-items:center;justify-content:center;min-height:400px;background:linear-gradient(135deg,#1e3a5f,#3d5f9a);color:#fff;padding:40px;text-align:center;font-family:system-ui,sans-serif"><div><h1 style="font-size:48px;margin:0 0 16px">课程标题</h1><p style="font-size:18px;opacity:0.85">课文标题</p></div></section>',
    'question-intro': '<div class="question-intro" style="padding:60px 40px;text-align:center;font-family:system-ui,sans-serif"><h2 style="font-size:24px;color:#1e3a5f;margin-bottom:16px">思考题</h2><p style="font-size:16px;color:#4b5563">在此输入引导问题...</p><div style="margin-top:20px"><button onclick="this.nextElementSibling.style.display=\'block\';this.style.display=\'none\'" style="padding:10px 32px;background:#3d5f9a;color:#fff;border:none;border-radius:8px;cursor:pointer">点击揭晓</button><div style="display:none;margin-top:12px;padding:12px;background:#eef3f9;border-radius:8px;color:#2f4b7d">答案区域</div></div></div>',
    'learning-goals': '<div style="padding:40px;font-family:system-ui,sans-serif"><h2 style="font-size:24px;color:#1e3a5f;margin-bottom:20px;text-align:center">学习目标</h2><div style="max-width:600px;margin:0 auto;display:flex;flex-direction:column;gap:12px"><div style="padding:14px 16px;background:#eef3f9;border-left:4px solid #3d5f9a;border-radius:4px"><strong>知识目标</strong><p style="margin:6px 0 0;color:#4b5563">在此输入...</p></div><div style="padding:14px 16px;background:#fef3c7;border-left:4px solid #f59e0b;border-radius:4px"><strong>能力目标</strong><p style="margin:6px 0 0;color:#4b5563">在此输入...</p></div></div></div>',
    'vocab-card': '<div class="vocab-card" style="padding:40px;max-width:600px;margin:0 auto;font-family:system-ui,sans-serif"><div style="text-align:center;margin-bottom:16px"><span style="font-size:32px;font-weight:700;color:#1e3a5f">vocabulary</span><span style="margin-left:8px;font-size:14px;color:#6b7280">/音标/</span></div><div style="background:#f9fafb;border-radius:10px;padding:20px"><p style="color:#374151;line-height:1.8;margin:0"><strong>释义：</strong>在此输入</p><p style="color:#374151;line-height:1.8;margin:8px 0 0"><strong>例句：</strong><em>在此输入例句...</em></p></div></div>',
    'sentence-breakdown': '<div style="padding:40px;font-family:system-ui,sans-serif;max-width:700px;margin:0 auto"><div style="background:#f9fafb;border-radius:10px;padding:20px;margin-bottom:16px;font-size:16px;line-height:1.8">在此粘贴长难句...</div><div style="display:flex;flex-direction:column;gap:8px"><div style="padding:12px 16px;background:#eef3f9;border-radius:6px"><strong>主语：</strong>点击展开</div><div style="padding:12px 16px;background:#fef3c7;border-radius:6px"><strong>谓语：</strong>点击展开</div></div></div>',
    'theory-card': '<div style="padding:32px;font-family:system-ui,sans-serif;max-width:600px;margin:0 auto"><div style="background:linear-gradient(135deg,#eef3f9,#d5e0ef);border-radius:10px;padding:20px"><div style="font-size:11px;color:#5b7ab3;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">理论依据</div><h3 style="font-size:16px;color:#1e3a5f;margin:0 0 8px">理论名称</h3><p style="font-size:13px;color:#374151;line-height:1.6;margin:0">教学决策的理论支撑...</p></div></div>',
    'text-segment': '<div style="padding:40px;font-family:system-ui,sans-serif;max-width:700px;margin:0 auto"><div style="padding:24px;background:#f9fafb;border-radius:10px;font-size:16px;line-height:2;color:#1f2937;margin-bottom:12px">在此粘贴课文段落...</div><div style="padding:12px 16px;background:#eef3f9;border-radius:6px;font-size:13px;color:#3d5f9a"><strong>阅读引导：</strong>在此输入问题...</div></div>',
    'compare-page': '<div style="padding:40px;font-family:system-ui,sans-serif;max-width:800px;margin:0 auto"><div style="display:grid;grid-template-columns:1fr 1fr;gap:20px"><div style="background:#f9fafb;border-radius:10px;padding:20px"><h4 style="font-size:15px;color:#1e3a5f;margin:0 0 8px">文本 A</h4><p style="font-size:13px;color:#6b7280">内容...</p></div><div style="background:#f9fafb;border-radius:10px;padding:20px"><h4 style="font-size:15px;color:#1e3a5f;margin:0 0 8px">文本 B</h4><p style="font-size:13px;color:#6b7280">内容...</p></div></div></div>',
    'group-discussion': '<div style="padding:40px;font-family:system-ui,sans-serif;max-width:650px;margin:0 auto"><h3 style="font-size:20px;color:#1e3a5f;margin:0 0 20px">小组讨论</h3><div style="display:grid;grid-template-columns:1fr 1fr;gap:12px"><div style="background:#f9fafb;border-radius:8px;padding:16px"><div style="font-size:11px;color:#6b7280">主题</div><div style="font-size:14px;font-weight:600;color:#1f2937">在此输入</div></div><div style="background:#f9fafb;border-radius:8px;padding:16px"><div style="font-size:11px;color:#6b7280">时间</div><div style="font-size:28px;font-weight:700;color:#3d5f9a">5:00</div></div><div style="background:#f9fafb;border-radius:8px;padding:16px"><div style="font-size:11px;color:#6b7280">分工</div><div style="font-size:13px;color:#374151">记录员 · 发言人</div></div><div style="background:#f9fafb;border-radius:8px;padding:16px"><div style="font-size:11px;color:#6b7280">输出</div><div style="font-size:13px;color:#374151">口头汇报</div></div></div></div>',
    'task-flow': '<div style="padding:40px;font-family:system-ui,sans-serif;max-width:650px;margin:0 auto"><h3 style="font-size:20px;color:#1e3a5f;margin:0 0 24px;text-align:center">课堂任务</h3><div style="display:flex;flex-direction:column;gap:0"><div style="display:flex;align-items:flex-start;gap:14px;padding:0 0 20px"><span style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;background:#3d5f9a;color:#fff;font-weight:700;font-size:14px;flex-shrink:0">1</span><div><div style="font-weight:600;font-size:15px">第一步</div><p style="font-size:13px;color:#6b7280;margin:4px 0 0">说明...</p></div></div><div style="display:flex;align-items:flex-start;gap:14px;padding:0 0 20px"><span style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;background:#3d5f9a;color:#fff;font-weight:700;font-size:14px;flex-shrink:0">2</span><div><div style="font-weight:600;font-size:15px">第二步</div><p style="font-size:13px;color:#6b7280;margin:4px 0 0">说明...</p></div></div></div></div>',
    'quiz-choice': '<div style="padding:40px;font-family:system-ui,sans-serif;max-width:600px;margin:0 auto"><h3 style="font-size:20px;color:#1e3a5f;margin:0 0 20px">课堂检测</h3><p style="font-size:15px;color:#374151;margin:0 0 20px">题干内容...</p><div style="display:flex;flex-direction:column;gap:8px"><div onclick="this.style.background=this.dataset.ok?\'#ecfdf5\':\'#fef2f2\';this.style.borderColor=this.dataset.ok?\'#10b981\':\'#ef4444\'" data-ok="false" style="padding:12px 16px;border:2px solid #e5e7eb;border-radius:8px;cursor:pointer;font-size:14px">A. 选项一</div><div onclick="this.style.background=this.dataset.ok?\'#ecfdf5\':\'#fef2f2\';this.style.borderColor=this.dataset.ok?\'#10b981\':\'#ef4444\'" data-ok="true" style="padding:12px 16px;border:2px solid #e5e7eb;border-radius:8px;cursor:pointer;font-size:14px">B. 选项二 ✓</div></div></div>',
    'reveal-answer': '<div style="padding:50px 40px;text-align:center;font-family:system-ui,sans-serif"><p style="font-size:20px;font-weight:600;color:#1e3a5f;margin-bottom:24px">在此输入问题...</p><button onclick="this.nextElementSibling.style.display=\'block\';this.style.display=\'none\'" style="padding:12px 32px;background:#3d5f9a;color:#fff;border:none;border-radius:8px;font-size:15px;cursor:pointer">揭晓答案</button><div style="display:none;margin-top:20px;padding:20px;background:#ecfdf5;border:2px solid #10b981;border-radius:10px;font-size:16px;font-weight:600;color:#065f46">答案</div></div>',
    'timer-block': '<div style="padding:50px 40px;text-align:center;font-family:system-ui,sans-serif"><div style="font-size:16px;color:#6b7280;margin-bottom:12px">限时练习</div><div style="font-size:64px;font-weight:800;color:#1e3a5f;cursor:pointer" onclick="var s=this,t=parseInt(s.dataset.sec||180),i=null;s.onclick=function(){if(i){clearInterval(i);i=null;return}i=setInterval(function(){t--;var m=Math.floor(t/60);s.textContent=m+\':\'+(t%60).toString().padStart(2,\'0\');if(t<=30)s.style.color=\'#ef4444\';if(t<=0){clearInterval(i);i=null}},1000)}" data-sec="180">3:00</div></div>',
    'summary-page': '<div style="padding:40px;font-family:system-ui,sans-serif;max-width:700px;margin:0 auto"><h2 style="font-size:24px;color:#1e3a5f;text-align:center;margin:0 0 28px">本课总结</h2><div style="display:grid;grid-template-columns:1fr 1fr;gap:12px"><div style="background:#eef3f9;border-radius:8px;padding:16px"><div style="font-weight:600;font-size:14px;color:#2f4b7d">核心词汇</div><p style="font-size:13px;color:#374151;margin:6px 0 0">在此输入...</p></div><div style="background:#fef3c7;border-radius:8px;padding:16px"><div style="font-weight:600;font-size:14px;color:#92400e">重点语法</div><p style="font-size:13px;color:#374151;margin:6px 0 0">在此输入...</p></div></div></div>',
    'reflection-card': '<div style="padding:50px 40px;font-family:system-ui,sans-serif;max-width:600px;margin:0 auto"><h3 style="font-size:22px;color:#1e3a5f;text-align:center;margin:0 0 24px">反思</h3><div style="display:flex;flex-direction:column;gap:12px"><div style="padding:14px 18px;background:#f9fafb;border-radius:8px"><strong>What did you learn?</strong><p style="margin:6px 0 0;color:#6b7280">在此输入...</p></div><div style="padding:14px 18px;background:#f9fafb;border-radius:8px"><strong>What remains unclear?</strong><p style="margin:6px 0 0;color:#6b7280">在此输入...</p></div></div></div>',
    'homework': '<div style="padding:40px;font-family:system-ui,sans-serif;max-width:600px;margin:0 auto"><h3 style="font-size:20px;color:#1e3a5f;margin:0 0 20px">课后任务</h3><div style="background:#f9fafb;border-radius:10px;padding:20px;margin-bottom:12px"><div style="font-weight:600;font-size:14px">必做</div><p style="font-size:13px;color:#6b7280;margin:6px 0 0;line-height:1.6">任务说明...</p></div><div style="background:#f9fafb;border-radius:10px;padding:20px"><div style="font-weight:600;font-size:14px">选做</div><p style="font-size:13px;color:#6b7280;margin:6px 0 0;line-height:1.6">任务说明...</p></div></div>',
    'teacher-notes': '<div class="teacher-note" style="padding:14px;background:#fef3c7;border-left:4px solid #f59e0b;border-radius:4px;font-size:12px;color:#92400e;margin:12px;font-family:system-ui,sans-serif"><strong>备注：</strong>在此输入...</div>',
    'focus-blackout': '<div style="padding:20px;font-family:system-ui,sans-serif;text-align:center;color:#6b7280;font-size:12px">[聚焦控制块 · 用于课堂展示时控制学生视线]</div>',
    'toc-overview': '<div style="padding:40px;font-family:system-ui,sans-serif"><h2 style="font-size:24px;color:#1e3a5f;text-align:center;margin:0 0 20px">目录</h2><div style="max-width:400px;margin:0 auto"><div style="padding:10px 0;border-bottom:1px solid #e5e7eb;font-size:14px;color:#374151">1. 导入</div><div style="padding:10px 0;border-bottom:1px solid #e5e7eb;font-size:14px;color:#374151">2. 讲授</div><div style="padding:10px 0;border-bottom:1px solid #e5e7eb;font-size:14px;color:#374151">3. 活动</div></div></div>',
  },

  create(type, targetDoc) {
    var html = this.templates[type];
    if (!html) {
      // Fallback: create a generic container for unknown types
      html = '<div style="padding:20px;font-family:system-ui,sans-serif" data-component="' + type + '">[' + type + '] 组件</div>';
    }
    var doc = targetDoc || document;
    var div = doc.createElement('div');
    div.innerHTML = html;
    var el = div.firstElementChild;
    if (el) {
      el.setAttribute('data-component', type);
      el.setAttribute('data-editable', 'true');
    }
    return el || div;
  },

  createFromHTML(htmlString, targetDoc) {
    var doc = targetDoc || document;
    var div = doc.createElement('div');
    div.innerHTML = htmlString;
    var el = div.firstElementChild;
    if (el) el.setAttribute('data-editable', 'true');
    return el || div;
  },

  getTemplate(type) {
    return this.templates[type] || null;
  },

  // Map component type → teaching stage
  stageMap: {
    'course-cover': '导入', 'question-intro': '导入', 'learning-goals': '导入',
    'vocab-card': '讲授', 'sentence-breakdown': '讲授', 'theory-card': '讲授',
    'text-segment': '阅读', 'compare-page': '阅读',
    'group-discussion': '活动', 'task-flow': '活动',
    'quiz-choice': '检测', 'reveal-answer': '检测', 'timer-block': '检测',
    'summary-page': '总结', 'reflection-card': '总结',
    'homework': '作业',
    'teacher-notes': '辅助', 'focus-blackout': '辅助',
  }
};
