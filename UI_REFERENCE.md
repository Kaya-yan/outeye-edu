# OutEye Edu 前端 UI 参考文档

> 本文档面向 UI 设计团队。目的：让设计同学在不读代码的情况下，了解当前前端的结构、页面、入口、配色、字体、组件，并能据此讨论设计改版方向。

---

## 一、整体技术栈

| 项目 | 技术 |
|------|------|
| 框架 | Next.js 14（App Router）+ React 18 |
| 语言 | TypeScript |
| 样式 | TailwindCSS |
| 图表 | Chart.js |
| 富文本 | Tiptap |
| 状态 | React Context（Auth） |
| 设计风格 | 学术 + 玻璃拟态 + 深蓝主色调 |

---

## 二、设计系统现状

### 1. 主色（primary，深蓝学术色）

```
50  #eef3f9  ← 最浅背景
100 #d5e0ef
200 #afc1df
300 #829cc9
400 #5b7ab3
500 #3d5f9a  ← 主色
600 #2f4b7d
700 #1e3a5f  ← Hero / CTA
800 #172d4a
900 #111f35
950 #0a1320  ← 最深
```

### 2. 辅助色

| 名称 | 用途 | 色值（500） |
|------|------|------------|
| accent (琥珀) | 强调 / 评分高亮 | #f59e0b |
| success (绿) | 成功状态 / RAG 标签 | #7c9a82 |
| navy (深蓝灰) | 文字 / 中性背景 | #627d98 |

### 3. 功能色（在页面中实际使用）

| 颜色 | 用途 |
|------|------|
| blue-50/600/700/800 | Wiki 理论 / 智能分析 |
| emerald-50/600 | RAG 检索 / 资源检索 |
| violet-50/600 | 知识库 / 应用层 |
| amber-50/600 | 项目管理 / 平台验证数据 |
| cyan-50/600 | 教材对比 |
| rose-50/600 | 专家评审 |
| red-50/200/600/700 | 错误提示 |
| green-100/300/800 | 步骤完成状态 |

### 4. 字体

```js
sans:   system-ui, -apple-system, Segoe UI, Microsoft YaHei, PingFang SC, sans-serif
serif:  Georgia, Noto Serif SC, serif
display: 同 sans
```

- 当前以系统字体为主，未引入自定义 Web 字体
- 中文 fallback：微软雅黑 / 苹方

### 5. 圆角 / 阴影

| Token | 值 | 用途 |
|-------|-----|------|
| rounded-lg | 8px | 输入框、按钮 |
| rounded-xl | 12px | 卡片、容器 |
| rounded-2xl | 16px | 大卡片、Hero 统计 |
| rounded-3xl | 24px | CTA 区域 |
| rounded-full | 全圆 | 主 CTA 按钮、标签 |
| shadow-soft | 极弱阴影 | 浮层 |
| shadow-card | 中阴影 | 卡片 |
| shadow-elevated | 强阴影 | 下拉菜单 |

### 6. 排版梯度（首页 Hero）

```
text-6xl  4xl 5xl 6xl 字号
tracking-tight
font-extrabold
mt-2 bg-gradient-to-r (渐变文字)
```

正文：
```
text-base / text-sm / text-xs
text-gray-500 / text-gray-700
leading-relaxed
```

### 7. 动效

| 类型 | 实现 |
|------|------|
| 渐入 | fadeIn / slideUp / scaleIn |
| Hover 抬升 | translateY(-1) + 阴影增强 |
| Stagger 错峰 | 80ms 间隔 |
| Glass 模糊 | backdrop-blur(16px) |
| Skeleton 骨架 | shimmer 动画 |
| Float 漂浮 | 6s/8s ease-in-out |

---

## 三、全局布局

### Layout 结构（layout.tsx）

```
┌─────────────────────────────────────┐
│ Navbar (sticky, h-16, 玻璃白)        │
├─────────────────────────────────────┤
│                                     │
│   Main Content (max-w-7xl)          │
│                                     │
├─────────────────────────────────────┤
│ Footer (border-t, 弱白)             │
└─────────────────────────────────────┘
```

- 顶部 3px 渐变线（primary-400 → 800）
- 背景：浅灰渐变（#f7f9fc → #f0f4f8 → #eef2f7）
- 最大宽度：max-w-7xl（1280px）
- 内边距：px-4 / sm:px-6 / lg:px-8

### Navbar 内容

| 位置 | 元素 |
|------|------|
| 左侧 | Logo（眼睛图标 + "OutEye" 黑 + "Edu" 蓝） |
| 左侧 | 导航：首页 / 项目管理 / 智能分析 / 资源库 / 知识库 |
| 右侧 | 通知铃铛（带红点） |
| 右侧 | 用户头像（首字母 + 下拉菜单：用户信息、退出登录） |
| 右侧（未登录） | "登录"按钮（蓝渐变） |
| 移动端 | 汉堡菜单 |

**导航高亮**：当前页 primary-600 + 底部 8px 宽 2px 高蓝条

---

## 四、页面清单（共 9 个）

### 4.1 首页 `/`

**目标**：展示产品定位、核心功能、理论支撑，引导用户开始使用。

**结构（从上到下）**：

1. **Hero 区**
   - 深蓝渐变背景（primary-700 → 600 → 800）
   - 浮动光晕装饰（3 个，blur 圆形）
   - 主标题（6xl，白色 + 渐变文字）
   - 副标题（lg，primary-100/90）
   - 两个 CTA：白底"开始分析" + 描边"我的项目"

2. **核心数据卡片**（浮在 Hero 下方）
   - 白色 2xl 圆角，强阴影
   - 4 列：12 大理论 / 6 维度分析 / RAG 智能检索 / AI 教案生成

3. **平台验证数据区**
   - 琥珀渐变背景（amber-50 → orange-50）
   - 4 项：教案质量 4.2/5、备课时间-47%、活动可实施性 4.5/5、5 位专家

4. **核心功能区**
   - 标题 + 副标题
   - 4+2 网格卡片：
     - 智能分析（blue）
     - 资源检索（emerald）
     - 知识库（violet）
     - 项目管理（amber）
     - 教材对比（cyan，可点击）
     - 专家评审（rose，可点击）
   - 每张卡：图标 + 标题 + 描述
   - Hover：上移 + 阴影增强

5. **技术架构区**（白底 + 上下分隔线）
   - 三层架构卡片：LLM Wiki / RAG / 应用层
   - 每层：渐变图标 + Layer 标签 + 标题 + 三行描述

6. **12 大理论区**
   - 4 列网格，12 个小卡
   - 编号 + 名称 + 描述
   - Hover：边框变蓝

7. **CTA 区**
   - 深蓝渐变圆角大卡（3xl）
   - 装饰圆点背景
   - "开始使用 OutEye Edu" + 两个按钮

**Footer**（全局）
- 眼睛图标 + "OutEye Edu"
- 版权 + 赛事说明

---

### 4.2 登录页 `/login`

- **不显示** Navbar
- 简洁居中卡片
- 字段：邮箱、密码
- 主按钮：登录（蓝）
- 底部链接：去注册

---

### 4.3 注册页 `/register`

- **不显示** Navbar
- 居中卡片
- 字段：用户名、邮箱、密码、确认密码
- 主按钮：注册
- 底部链接：去登录

---

### 4.4 智能分析页 `/analysis`（核心页）

**目标**：四步流程完成"课文 → 分析 → 检索 → 教案"。

**页面布局**：
```
┌─────────────────────────────────┐
│ 标题 + 副标题（ADDSR-Lite）       │
├─────────────────────────────────┤
│ Stepper（4 步进度条）             │
├─────────────────────────────────┤
│                                 │
│   Step Content（按当前步骤切换）  │
│                                 │
└─────────────────────────────────┘
```

**Stepper 4 步**：

| 步骤 | 标签 | 图标 | 颜色 |
|------|------|------|------|
| 1 | 输入课文 | 📝 | primary（当前）/ green（完成）/ gray（未达） |
| 2 | 白盒分析 | 📊 | 同上 |
| 3 | 双源检索 | 🔍 | 同上 |
| 4 | 教学方案 | 📋 | 同上 |

**Step 1 输入课文**：
- 文件上传区（FileUploadZone，拖拽 + 点击）
- 分隔线 "或手动输入"
- 课文标题输入框
- 学生水平（A1-C2 按钮，6 个）
- 课文语种下拉（自动检测 + 6 种语言）
- 学生画像（折叠面板）：学生母语、课程类型、班级人数
- 富文本编辑器（Tiptap）
- 字数统计（实时）
- 主按钮："开始白盒分析"

**Step 2 白盒分析结果**：
- 耗时显示
- WhiteboxResults 组件（见下方组件说明）
- 按钮："返回修改" + "下一步：双源检索"

**Step 3 双源检索结果**：
- 2 列统计卡：Wiki 理论数（blue-50/700）+ RAG 资源数（green-50/700）
- Wiki 结果列表（蓝底卡片，标题 + 相关度 + 摘要）
- RAG 结果列表（绿底卡片，标题 + 相关度 + 内容）
- 空状态："未检索到相关资源"
- 按钮："返回分析" + "生成教学方案"（loading：AI 生成中...）

**Step 4 教学方案**：
- 顶部标签云（enhancement_tags，蓝底圆角）
- TeachingPlanView 组件（见组件说明）
- 导出按钮组：PPTX / DOCX / HTML
- 修订功能（基于教师反馈）
- 底部："分析新课文"

---

### 4.5 文本对比页 `/compare`

**目标**：多篇课文难度并排对比。

- 顶部添加文本按钮
- 多列卡片并排
- 每列显示一篇课文的关键指标
- 支持白盒指标对比

---

### 4.6 项目管理页 `/projects`

**目标**：管理用户分析过的项目。

- 项目列表（卡片或表格）
- 状态筛选（全部 / 进行中 / 已完成）
- 每项：标题、时间、状态、操作
- 调用 `GET /projects/`

---

### 4.7 资源库页 `/resources`

**目标**：RAG 驱动的教学资源检索。

- 搜索框（查询输入）
- Wiki 开关（是否启用双源检索）
- 文件上传按钮（为 RAG 索引添加文档）
- 结果列表：标题 + 相关度 + 摘要
- 调用 `POST /rag/query` 或 `POST /rag/query-with-wiki`

---

### 4.8 知识库页 `/knowledge`

**目标**：浏览 12 大语言学理论。

- 顶部标签云（所有理论标签）
- 搜索框
- 理论列表（点击展开详情）
- 详情页：核心概念、工程化映射、算法实现、Prompt 模板、参考文献
- 调用 `GET /wiki/tags`、`GET /wiki/search`、`GET /wiki/theory/{name}`

---

### 4.9 专家评审页 `/expert-review`

**目标**：展示专家评审数据 + 提交新评审。

- 顶部统计区（公开数据）
- 评审列表
- 提交评审表单（5 维度打分）
- 调用 `GET /expert-review/stats`、`POST /expert-review/submit`

---

## 五、核心组件清单

### 5.1 WhiteboxResults（白盒分析结果展示）

**位置**：`src/components/WhiteboxResults.tsx`（332 行）

**展示内容**：
- 课文级别 + 语言 + 耗时
- 词汇统计：总词数、独特词、TTR、AWL 占比
- CEFR 分布（柱状图 CefrBarChart）
- 难词列表（DifficultWordsChart）
- 句法统计：句子数、平均句长、Flesch 阅读容易度（ReadabilityGauge）
- 语篇分析：段落数、衔接密度、体裁、教学要点
- 学习者差距：text_level vs student_level
- 教学洞察：metric / value / implication / action / confidence
- 文化元素：类别 + 关键词 + 语境 + 解释
- 增强标签（enhancement_tags）

### 5.2 TeachingPlanView（教学方案展示）

**位置**：`src/components/TeachingPlanView.tsx`（438 行）

**展示内容**：
- 难度概览
- 教学建议列表
- 活动设计（名称 / 目标 / 步骤 / 时长）
- 差异化策略
- 理论依据
- 来源引用（Wiki / RAG）
- 模型信息 + 耗时
- 导出按钮组
- 修订输入区

### 5.3 FileUploadZone（文件上传）

**位置**：`src/components/FileUploadZone.tsx`（283 行）

**功能**：
- 拖拽 + 点击上传
- 支持 PDF / DOCX / TXT / MD
- 图片 OCR（JPG / PNG / WebP）
- 页码选择（PDF）
- OCR 预览
- 文本提取回调

### 5.4 TiptapEditor（富文本编辑器）

**位置**：`src/components/TiptapEditor.tsx`（127 行）

**功能**：
- 富文本编辑（粗体、斜体、列表等）
- 用于课文内容输入
- SSR 动态加载

### 5.5 图表组件（4 个）

| 组件 | 用途 | 类型 |
|------|------|------|
| RadarChart | 六维分析雷达图 | Chart.js Radar |
| CefrBarChart | CEFR 等级分布 | Chart.js Bar |
| DifficultWordsChart | 难词分布 | Chart.js Bar |
| ReadabilityGauge | 可读性仪表盘 | Chart.js Gauge |

### 5.6 其他组件

| 组件 | 行数 | 用途 |
|------|------|------|
| Navbar | 142 | 顶部导航 |
| ClientProviders | 8 | 客户端 Provider 包装 |
| OCRPreview | 75 | OCR 结果预览 |
| PageRangeSelector | 131 | PDF 页码选择 |

---

## 六、功能入口地图

```
首页 (/)
├── 开始分析 ─────────────→ /analysis
├── 我的项目 ─────────────→ /projects
├── 教材对比 ─────────────→ /compare
└── 专家评审 ─────────────→ /expert-review

Navbar
├── 首页 ─────────────────→ /
├── 项目管理 ─────────────→ /projects
├── 智能分析 ─────────────→ /analysis
├── 资源库 ───────────────→ /resources
└── 知识库 ───────────────→ /knowledge

分析页流程
├── Step1 输入 ─→ POST /analysis/parse-file（文件解析）
│                POST /analysis/ocr-image（图片 OCR）
│                POST /analysis/whitebox（白盒分析）
├── Step2 分析 ─→ WhiteboxResults 展示
├── Step3 检索 ─→ POST /analysis/retrieve（双源检索）
└── Step4 方案 ─→ POST /analysis/generate-plan（生成教案）
                 POST /analysis/revise-plan（修订）
                 POST /analysis/export（导出 PPTX/DOCX/HTML）
```

---

## 七、设计现状的观察（供设计团队参考）

### 优点
1. **配色统一**：深蓝主色贯穿全局，学术感强
2. **玻璃拟态**：Navbar + 卡片有现代感
3. **动效克制**：Hover、渐入、Stagger 都有但不喧宾夺主
4. **信息密度合理**：首页大段留白 + 功能区紧凑

### 可改进点
1. **字体**：纯系统字体，缺少品牌识别度，可考虑引入一套衬线/无衬线组合
2. **图标**：全部用内联 SVG，风格统一但数量有限
3. **首页 Hero**：装饰光效偏多，可能分散注意力
4. **分析页**：四步流程较线性，缺少"返回某步"的快捷入口
5. **图表配色**：Chart.js 默认色未与主色系统完全对齐
6. **移动端**：Navbar 汉堡菜单未实现展开逻辑
7. **空状态**：部分页面缺少插图式空状态

### 设计讨论建议方向
- 是否引入品牌字体（如思源系列 + 西文衬线）
- 是否为 12 大理论设计独立视觉符号
- 图表是否统一到 primary 色系
- 分析页是否改为左侧步骤栏 + 右侧内容的双栏布局
- 是否增加深色模式

---

**文档版本**：v1.0
**生成日期**：2026-07-20
**适用项目**：OutEye Edu 1.0
