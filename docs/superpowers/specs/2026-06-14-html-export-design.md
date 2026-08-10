# 教学方案 HTML 导出功能 — 设计规格

> OutEye Edu 3.0 · 智能教研操作系统
> 最后更新：2026-06-14

## 1. 概述

### 1.1 目标

为 OutEye Edu 设计交互式 HTML 导出功能，将白盒分析数据 + LLM 生成的教案融合为一个独立、可投屏、可编辑的 HTML 文件，供教师课堂直接使用。

### 1.2 设计原则

- **独立自包含**：单个 .html 文件，无外部依赖，离线可用
- **课堂优先**：深色主题优化投影仪显示，大字体，高对比度
- **教师可控**：白板批注、内容编辑、逐步揭示、倒计时
- **去 AI 感**：暖色调（琥珀/紫色），有机动效，非网格化布局
- **模板可复用**：数据与模板分离，支持多场景多学科扩展

### 1.3 理论基础

| 理论 | 应用 |
|------|------|
| 认知负荷理论 (Sweller) | 分块呈现、渐进揭示、视觉层次 |
| Mayer 多媒体学习 12 原则 | 多通道呈现、时间邻近、冗余消除 |
| 双重编码理论 (Paivio) | 词汇云 + CEFR 柱状图可视化 |
| i+1 输入假说 (Krashen) | 难度差距设计，数据标注 |
| ZPD 最近发展区 (Vygotsky) | 支架教学、小组合作活动设计 |

---

## 2. 架构

### 2.1 方案选择：独立 HTML 模板 + 数据注入

```
教师输入课文 → 白盒分析 → LLM 融合生成教案
        ↓
系统选择模板（按学科/课型/难度）
        ↓
分析数据 + 教案数据注入模板 → 生成 .html
        ↓
教师下载 → 课上使用 / 修改 / 反馈
        ↓
优质 .html 回流知识库 → 成为未来模板参考
```

### 2.2 数据注入方式

- HTML 文件中用 `{{data.xxx}}` 占位符标记注入点
- 数据以 JSON 形式内嵌在 `<script id="plan-data">` 标签中
- JS 读取 JSON 后渲染到 DOM，教师可修改 JSON 微调内容
- Python 后端读取模板后做字符串替换生成最终 .html

### 2.3 模板扩展路径

| 场景 | 模板文件 |
|------|----------|
| 大学英语 | `template_college.html` |
| 高中英语 | `template_highschool.html` |
| 阅读课 | `template_reading.html` |
| 写作课 | `template_writing.html` |
| 新场景 | 新模板文件，零代码改动 |

---

## 3. 入场动画

### 3.1 设计目标

品牌级 AR 风格启动序列，约 3.2 秒，传达科技感和专业感。

### 3.2 动画序列

| 时间 | 元素 | 效果 |
|------|------|------|
| 0.0s | Canvas 粒子 | 80 个浮动粒子 + 连线网络，琥珀色半透明 |
| 0.6s | Logo 文字 | `translateY(20px) + blur(8px)` → 原位，cubic-bezier(0.16,1,0.3,1) |
| 0.6s | Glitch 特效 | Logo 的 ::before(红) 和 ::after(青) 层随机 clip-path + translate |
| 0.8-1.1s | HUD 四角框 | 从 scale(1.5) 缩至 scale(1)，依次出现 |
| 1.2s | 副标题 | `translateY(10px)` 淡入，letter-spacing: 4px |
| 1.4s | 进度条 | 2px 高度，背景灰，::after 渐变填充 |
| 1.6-2.8s | 进度填充 | `width: 0 → 100%`，cubic-bezier(0.22,1,0.36,1) |
| 3.2s | 退出 | `.intro` 添加 `.hide` 类，opacity 0 + visibility hidden |

### 3.3 技术实现

- **粒子系统**：Canvas API，requestAnimationFrame 循环，80 个粒子带速度向量
- **连线**：粒子间距离 < 150px 时绘制连线，透明度随距离衰减
- **扫描线**：`::after` 伪元素，`repeating-linear-gradient`，2px 间隔
- **Glitch**：`@keyframes` + `clip-path: inset()` 随机裁切 + `translate` 偏移

---

## 4. 白板批注系统

### 4.1 工具

| 工具 | 快捷键 | 光标形态 | 说明 |
|------|--------|----------|------|
| 画笔 | P | 实心圆点 | 自由绘制 |
| 荧光笔 | H | 较大半透明圆 | 低透明度涂抹 |
| 文字 | X | I 形光标 | 点击输入文字 |
| 圆形 | C | 十字准星 | 拖拽画圆 |
| 箭头 | A | 十字准星 | 拖拽画箭头 |
| 橡皮擦 | R | 虚线圆圈 | `destination-out` 擦除 |

### 4.2 光标系统

- 全局 `cursor: none`，使用 DOM 元素 `.custom-cursor` 跟随鼠标
- pointermove 事件更新位置：`left = clientX - size/2`
- 每个工具切换时更新光标尺寸、边框样式、背景色
- 橡皮擦：40px 虚线圆；画笔：`max(size*2, 8)` 实心；文字：24px 无背景

### 4.3 工具指示器

- 浮动在顶栏下方居中位置
- 显示：工具颜色点 + 工具名称 + 线宽 + "退出 ✕" 按钮
- 进入白板时 show，退出时 hide

### 4.4 退出机制

- Esc 键退出（优先级：白板 → 激光笔 → 编辑模式 → 计时器）
- 工具指示器 "退出 ✕" 按钮
- 顶栏白板按钮再次点击

### 4.5 绘制技术

- Canvas API + pointer events
- 路径使用 quadraticCurveTo 平滑连接
- 荧光笔：`globalAlpha = 0.35`，线宽 `size * 3`
- 橡皮擦：`globalCompositeOperation = 'destination-out'`
- 支持撤销（路径栈 pop）和清除全部

---

## 5. 交互特性

### 5.1 3D 倾斜卡片

- 所有 `.tilt-card` 元素响应 mousemove
- 计算鼠标相对位置：`(clientX - left) / width - 0.5`
- 应用变换：`perspective(600px) rotateY(x*6deg) rotateX(-y*6deg) scale3d(1.01,1.01,1.01)`
- mouseleave 时回弹：`transition: transform 0.4s ease`

### 5.2 逐步揭示

- 活动步骤使用 `.reveal-step` 组件
- 初始状态：步骤图标 + 灰色占位条，文字隐藏（max-width: 0）
- 点击后：占位条消失，文字展开（max-width: 600px），图标变色
- 空格键全局触发：揭示当前面板第一个未揭示步骤

### 5.3 倒计时器

- SVG 圆形进度环，`stroke-dashoffset` 动态计算
- 预设：1/3/5/10 分钟
- 颜色变化：>50% 绿色，>25% 橙色，<25% 红色
- 最后 10 秒脉冲动画
- 时间到闪烁提醒
- 背景遮罩，点击外部关闭

### 5.4 编辑模式

- 切换后所有 `[contenteditable]` 元素变为可编辑
- 编辑态显示虚线边框（`outline: 2px dashed var(--amber)`）
- 教师可直接修改建议文本、活动描述、理论说明

### 5.5 激光笔

- 红色圆点 + 发光阴影（`box-shadow: 0 0 10px, 0 0 20px`）
- pointermove 跟踪
- 与白板互斥

### 5.6 标签切换

- 5 个标签：难度概述 / 教学建议 / 活动设计 / 理论依据 / 数据参考
- 数字键 1-5 快速切换
- 切换时重新触发入场动画（`.anim-item` 重置 + 交错延迟 70ms）

---

## 6. 页面结构

### 6.1 标签页

| 标签 | 内容 |
|------|------|
| 难度概述 | 统计卡片（课文等级/学生水平/难度差距/可读性）+ 概述文本 |
| 教学建议 | 5 条建议，每条附数据分析依据 |
| 活动设计 | 3 个可展开活动卡片，含逐步揭示步骤 |
| 理论依据 | 3 张理论卡片（Krashen/Swain/Vygotsky） |
| 数据参考 | 词汇分析/句法分析/语篇分析双栏布局 |

### 6.2 统计卡片

- 4 列网格，`Noto Serif SC` 大号数字
- 数字动画：easeOutCubic 从 0 到目标值
- hover 时顶部渐变条显现

### 6.3 数据可视化

- CEFR 分布柱状图：`scaleX(0 → 1)` 生长动画
- 词汇云：浮动动画（`translateY(0 → -3px)`），hover 上浮
- 长句展示：红色边框卡片，斜体文本

---

## 7. 视觉设计

### 7.1 色彩系统

```css
--bg: #08081a        /* 深色背景，投影仪友好 */
--surface: #13132b   /* 卡片背景 */
--amber: #f5a623     /* 主强调色，暖色 */
--blue: #5b9ef5      /* 数据提示 */
--green: #4ade80     /* 正面指标 */
--red: #f87171       /* 警示 */
--purple: #a78bfa    /* 理论区块 */
```

### 7.2 字体

- 标题：Noto Serif SC（衬线，权威感）
- 正文：Noto Sans SC（无衬线，易读）
- 数据：Noto Serif SC + tabular-nums

### 7.3 毛玻璃效果

- 顶栏和底栏：`backdrop-filter: blur(24px)` + 半透明背景
- 工具栏和计时器：同样处理

### 7.4 环境光

- 两个大尺寸模糊圆形（orb），琥珀色和紫色
- 25 秒周期浮动动画
- opacity: 0.06，不干扰内容

---

## 8. 快捷键

| 按键 | 功能 |
|------|------|
| W | 切换白板 |
| L | 切换激光笔 |
| T | 打开/关闭计时器 |
| E | 切换编辑模式 |
| Space | 揭示下一个步骤 |
| 1-5 | 切换标签页 |
| ? | 显示帮助 |
| Esc | 退出当前模式 |
| Ctrl+Z | 撤销批注 |

白板模式内：P/H/X/C/A/R 切换工具

---

## 9. 数据结构

### 9.1 注入数据 JSON 结构

```json
{
  "meta": {
    "title": "课文标题",
    "model": "deepseek-chat",
    "generated_at": "2026-06-14",
    "level_from": "B2",
    "level_to": "B1",
    "tags": ["学术词汇密集", "长句存在"]
  },
  "overview": {
    "summary": "课文难度概述文本...",
    "stats": {
      "text_level": "B2",
      "student_level": "B1",
      "gap": "i+1",
      "flesch": 42.3
    },
    "data_hint": "301 词 · 16 句 · ..."
  },
  "suggestions": [
    {
      "text": "建议内容...",
      "data_hint": "数据支撑..."
    }
  ],
  "activities": [
    {
      "name": "活动名称",
      "icon": "🎯",
      "duration": "10 分钟",
      "objective": "活动目标...",
      "steps": ["步骤1", "步骤2"],
      "data_hint": "数据支撑..."
    }
  ],
  "theories": [
    {
      "name": "理论名称",
      "author": "作者, 年份",
      "description": "理论描述...",
      "tags": ["标签1", "标签2"]
    }
  ],
  "data": {
    "vocabulary": {
      "total_words": 301,
      "unique_words": 217,
      "awl_count": 37,
      "awl_percent": 12.3,
      "ttr": 0.72,
      "cefr_distribution": { "A1-A2": 45, "B1-B2": 30, "C1": 8, "unclassified": 17 },
      "out_of_level_words": [
        { "word": "acquisition", "level": "B2" }
      ]
    },
    "syntax": {
      "sentence_count": 16,
      "avg_sentence_length": 18.7,
      "long_sentences": 6,
      "very_long_sentences": 1,
      "longest_sentence": { "index": 3, "words": 42, "text": "..." }
    },
    "discourse": {
      "paragraph_count": 4,
      "connector_density": 3.2,
      "genre": "议论文"
    }
  }
}
```

---

## 10. 后端集成

### 10.1 生成流程

1. `export_service.py` 中新增 `export_html()` 函数
2. 读取模板文件（从模板库按场景选择）
3. 将白盒分析结果 + LLM 教案数据组装为 JSON
4. 字符串替换 `{{data.xxx}}` 占位符
5. 将 JSON 内嵌到 `<script id="plan-data">` 标签
6. 返回 .html 文件供下载

### 10.2 模板管理

- 模板存储路径：`templates/html/`
- 每个模板包含完整的 HTML + CSS + JS
- 数据注入点使用 `{{data.xxx}}` 标记
- 后续支持从知识库检索优质模板

### 10.3 前端集成

- 导出对话框新增 "HTML（交互式）" 格式选项
- 选择后调用后端 `export_html` API
- 返回 .html 文件自动下载

---

## 11. 知识库回流

优质 HTML 教案可回流知识库：
- 教师修改后的版本可上传保存
- 作为 RAG 检索的参考案例
- LLM 生成新教案时参考已有优秀模板
- 按学科/课型/难度分类存储
