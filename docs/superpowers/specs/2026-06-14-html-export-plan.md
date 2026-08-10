# 教学方案 HTML 导出 — 实现计划

> 基于设计规格：`docs/superpowers/specs/2026-06-14-html-export-design.md`
> 参考原型：`.superpowers/brainstorm/2025-1781427643/content/mockup-v4.html`

## 任务清单

### 任务 1：创建 HTML 模板文件

**文件**：`backend/templates/html/classroom_default.html`

**做什么**：
- 基于 mockup-v4.html 创建模板文件
- 将硬编码数据替换为 `{{data.xxx}}` 占位符
- 在 `<script id="plan-data">` 标签中预留 JSON 注入点 `{{data.json}}`
- JS 初始化代码从 `#plan-data` 读取 JSON 并渲染到 DOM
- 保留所有交互功能（白板、激光笔、计时器、3D倾斜、逐步揭示等）

**关键占位符**：
```
{{data.title}}          — 课文标题
{{data.model}}          — 模型名称
{{data.generated_at}}   — 生成时间
{{data.level_from}}     — 课文等级
{{data.level_to}}       — 学生水平
{{data.gap}}            — 差距描述
{{data.tags_html}}      — 标签 HTML
{{data.json}}           — 完整 JSON 数据
```

**验证**：模板文件可被浏览器直接打开（带默认占位数据），所有交互功能正常。

---

### 任务 2：后端 export_html() 函数

**文件**：`backend/app/services/analysis/export_service.py`

**做什么**：
- 新增 `export_html(plan, whitebox_data, title)` 函数
- 读取模板文件 `backend/templates/html/classroom_default.html`
- 将 `plan`（教案）和 `whitebox_data`（白盒分析）组装为 JSON
- 生成标签 HTML（从 whitebox_data 的 tags/enhanced_tags）
- 字符串替换所有 `{{data.xxx}}` 占位符
- 返回 `BytesIO` 对象

**数据映射**：
```python
json_data = {
    "meta": {
        "title": title,
        "model": plan.get("model", "unknown"),
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "level_from": whitebox_data.get("cefr_level", "B2"),
        "level_to": plan.get("learner_gap", {}).get("student_level", "B1"),
        "gap": plan.get("learner_gap", {}).get("gap", "i+1"),
    },
    "overview": {
        "summary": plan.get("difficulty_overview", ""),
        "flesch": whitebox_data.get("readability", {}).get("flesch_reading_ease", 0),
        "stats_hint": f"{whitebox_data.get('word_count', 0)} 词 · {whitebox_data.get('sentence_count', 0)} 句 · ..."
    },
    "suggestions": [
        {"text": s, "data_hint": ""} for s in plan.get("teaching_suggestions", [])
    ],
    "activities": [
        {
            "name": a.get("name", "课堂活动"),
            "icon": "🎯",
            "duration": a.get("duration", ""),
            "objective": a.get("objective", ""),
            "steps": a.get("steps", "").split("\n") if isinstance(a.get("steps"), str) else a.get("steps", []),
            "data_hint": ""
        }
        for a in plan.get("activity_designs", [])
    ],
    "theories": _parse_theory(plan.get("theoretical_basis", "")),
    "data": {
        "vocabulary": whitebox_data.get("vocabulary", {}),
        "syntax": whitebox_data.get("syntax", {}),
        "discourse": whitebox_data.get("discourse", {}),
    }
}
```

**验证**：单元测试传入 mock 数据，确认生成的 HTML 包含正确的 JSON 数据。

---

### 任务 3：后端 API 端点更新

**文件**：`backend/app/api/api_v1/endpoints/analysis_whitebox.py`

**做什么**：
- `ExportRequest.format` 字段增加 `"html"` 选项
- 在 `/export` 端点中添加 `elif request.format == "html"` 分支
- 调用 `export_html()`，传入 `request.plan` 和白盒分析数据
- 白盒数据从 `request.plan` 中提取（它已包含 `learner_gap` 等信息）
- 返回 `StreamingResponse`，media_type 为 `text/html`

**修改点**（约 5 行）：
```python
# line 577: format 字段描述更新
format: str = Field("pptx", description="导出格式: pptx, docx 或 html")

# line 596-605: 添加 html 分支
elif request.format == "html":
    buffer = export_html(request.plan, request.title)
    filename = f"{request.title}.html"
    media_type = "text/html; charset=utf-8"
```

**验证**：`POST /export` 带 `format: "html"` 返回有效 HTML 文件。

---

### 任务 4：前端导出 UI 更新

**文件**：`frontend/src/components/TeachingPlanView.tsx`

**做什么**：
- `onExport` 类型从 `"pptx" | "docx"` 扩展为 `"pptx" | "docx" | "html"`
- 在导出按钮区域新增第三个按钮："导出 HTML"
- 按钮样式：紫色渐变，区分于 PPT（橙色）和 Word（蓝色）
- 下载文件名改为 `教学方案.html`

**文件**：`frontend/src/app/analysis/page.tsx`

**做什么**：
- `handleExport` 函数的 format 参数类型扩展
- 下载文件名中的扩展名跟随 format

**验证**：点击"导出 HTML"按钮，浏览器下载 .html 文件，双击可在浏览器中打开并使用全部功能。

---

### 任务 5：模板目录结构

**新增目录**：
```
backend/templates/
  html/
    classroom_default.html    # 默认课堂投屏模板
```

**后续扩展**：
```
backend/templates/
  html/
    classroom_default.html    # 大学英语默认
    highschool_default.html   # 高中英语
    reading_default.html      # 阅读课
    writing_default.html      # 写作课
```

---

## 执行顺序

```
任务 1 (模板文件)  ←  最重要，其他任务依赖它
    ↓
任务 2 (export_html 函数)
    ↓
任务 3 (API 端点) + 任务 4 (前端 UI)  ←  可并行
    ↓
任务 5 (目录结构)  ←  已在任务 1 中完成
```

## 文件变更清单

| 操作 | 文件 |
|------|------|
| 新建 | `backend/templates/html/classroom_default.html` |
| 修改 | `backend/app/services/analysis/export_service.py` |
| 修改 | `backend/app/api/api_v1/endpoints/analysis_whitebox.py` |
| 修改 | `frontend/src/components/TeachingPlanView.tsx` |
| 修改 | `frontend/src/app/analysis/page.tsx` |
