# 课文输入体验优化 — 设计规格

> OutEye Edu 3.0 · 智能教研操作系统
> 最后更新：2026-06-14

## 1. 概述

### 1.1 问题

当前课文分析页面只能通过复制粘贴或手动打字输入文本，体验差。实际教学场景中，老师经常手头有教材 PDF、Word 教案、或随手拍的课文照片。

### 1.2 目标

- 支持上传 PDF / Word / TXT 文件，自动提取文本填入编辑器
- 支持上传课文照片，通过 OCR 识别文字
- PDF 支持指定页码范围分析
- 上传后文本可编辑修改，保持现有编辑器体验

### 1.3 设计决策

| 决策点 | 选择 | 原因 |
|--------|------|------|
| OCR 方案 | 阿里云 OCR + LLM 视觉降级 | 精度高、成本低，LLM 兜底处理复杂情况 |
| 页码选择 | 下拉选择 + 页面预览条 | 比纯输入框直观，比缩略图轻量 |
| UI 布局 | 合并式（上传区在编辑器上方） | 上传后可继续编辑，灵活 |
| 识别预览 | 先预览后确认 | 避免 OCR 错误直接进入分析 |

---

## 2. 整体布局

### 2.1 InputStep 组件改造

当前 InputStep 只有：标题输入 + 学生水平选择 + TiptapEditor + 提交按钮。

改造后结构：

```
InputStep
├── 文件上传区（新增）
│   ├── 拖拽/点击上传区域
│   ├── 文件信息展示（文件名、总页数）
│   ├── PDF 页码范围选择器
│   ├── 图片识别结果预览
│   └── 确认/重试按钮
├── 标题输入（已有）
├── 学生水平选择（已有）
├── TiptapEditor（已有，上传文本自动填入）
└── 提交按钮（已有）
```

### 2.2 交互流程

**文件上传流程：**
1. 用户拖拽或点击上传文件
2. 前端发送文件到 `/analysis/parse-file`
3. 后端解析文件，返回 `{ text, total_pages, filename }`
4. 如果是 PDF（多页），显示页码范围选择器
5. 用户选择范围后，前端再次请求（带 page_from/page_to 参数）
6. 解析文本填入 TiptapEditor
7. 用户可编辑修改，然后点击"开始白盒分析"

**图片 OCR 流程：**
1. 用户上传一张或多张图片
2. 前端发送图片到 `/analysis/ocr-image`
3. 后端调用阿里云 OCR 识别文字
4. 返回识别文本，前端展示预览
5. 用户确认 → 文本填入编辑器
6. 用户重试 → 重新调用 OCR（可选择 LLM 视觉降级）

---

## 3. 后端设计

### 3.1 新增 API 端点

#### `POST /analysis/parse-file`

上传文件并解析为文本。不入库，纯解析。

**请求：** `multipart/form-data`
- `file`: 文件（PDF/Word/TXT/MD）
- `page_from`: 起始页码（可选，PDF 专用）
- `page_to`: 结束页码（可选，PDF 专用）

**响应：**
```json
{
  "text": "解析后的纯文本...",
  "filename": "教材第三章.pdf",
  "total_pages": 52,
  "page_from": 15,
  "page_to": 20,
  "word_count": 1250,
  "file_type": "pdf"
}
```

**逻辑：**
1. 验证文件类型和大小（10MB 限制）
2. 保存到临时文件
3. 根据文件类型调用对应解析器
4. PDF 支持页码范围提取（PyPDF2 的 `pages[from:to]`）
5. 返回解析结果，删除临时文件

#### `POST /analysis/ocr-image`

上传图片并 OCR 识别文字。

**请求：** `multipart/form-data`
- `file`: 图片文件（JPG/PNG/WebP）
- `engine`: 识别引擎，`aliyun`（默认）或 `llm`

**响应：**
```json
{
  "text": "识别出的文本...",
  "confidence": 0.92,
  "engine": "aliyun",
  "word_count": 320
}
```

**逻辑：**
1. 验证图片格式和大小
2. 如果 engine=aliyun：调用阿里云通用文字识别 API
3. 如果 engine=llm：调用 DeepSeek/Mimo 多模态模型，发送图片请求识别文字
4. 返回识别结果

### 3.2 阿里云 OCR 集成

使用阿里云「通用文字识别」服务：

```python
# 新增文件：backend/app/services/ocr/aliyun_ocr.py
from alibabacloud_ocr_api20210707.client import Client
from alibabacloud_ocr_api20210707 import models as ocr_models

class AliyunOCR:
    def __init__(self, access_key_id: str, access_key_secret: str):
        self.client = Client(...)
    
    def recognize(self, image_bytes: bytes) -> dict:
        # 调用 RecognizeGeneral API
        # 返回 { text, confidence }
```

**配置项（.env）：**
```
ALIYUN_OCR_ACCESS_KEY_ID=
ALIYUN_OCR_ACCESS_KEY_SECRET=
ALIYUN_OCR_ENDPOINT=ocr-api.cn-hangzhou.aliyuncs.com
```

### 3.3 LLM 视觉降级

当阿里云 OCR 不可用或用户主动选择时，使用 LLM 多模态能力：

```python
# 使用 DeepSeek 或 Mimo 的视觉模型
# 将图片 base64 发送给 LLM，prompt: "请识别图片中的所有文字，保持原始格式"
```

### 3.4 PDF 页码提取

复用已有 PyPDF2，增加页码范围支持：

```python
from PyPDF2 import PdfReader

def extract_pages(file_path: str, page_from: int = None, page_to: int = None) -> tuple[str, int]:
    reader = PdfReader(file_path)
    total = len(reader.pages)
    start = (page_from - 1) if page_from else 0
    end = page_to if page_to else total
    text = "\n".join(reader.pages[i].extract_text() for i in range(start, end))
    return text, total
```

---

## 4. 前端设计

### 4.1 新增组件

#### `FileUploadZone.tsx`

文件上传区域组件，包含：
- 拖拽上传区（虚线框 + 图标 + 提示文字）
- 文件类型验证（前端校验扩展名）
- 上传进度显示
- 支持的格式提示：PDF / Word / TXT / 照片

#### `PageRangeSelector.tsx`

PDF 页码范围选择器：
- 总页数显示
- 范围模式下拉："全部页面" / "自定义范围"
- 起始页/结束页下拉（联动校验）
- 页面预览条（小方块 + 选中范围高亮）
- 提示文字："将提取第 15-20 页的内容"

#### `OCRPreview.tsx`

OCR 识别结果预览：
- 识别文本展示（可滚动）
- 识别引擎标签（阿里云 / LLM）
- "确认使用" 按钮 → 填入编辑器
- "重新识别" 按钮 → 重试
- "切换引擎" 按钮 → 降级到 LLM

### 4.2 InputStep 改造

在现有 InputStep 的标题输入上方，插入文件上传区：

```tsx
function InputStep({ ... }) {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">输入课文</h2>

        {/* 新增：文件上传区 */}
        <FileUploadZone
          onTextExtracted={(text) => setText(text)}
          onFileInfo={(info) => setFileInfo(info)}
        />

        {/* 已有：标题、水平、编辑器、提交按钮 */}
        ...
      </div>
    </div>
  );
}
```

### 4.3 API 调用

```typescript
// 解析文件
async function parseFile(file: File, pageFrom?: number, pageTo?: number) {
  const formData = new FormData();
  formData.append("file", file);
  if (pageFrom) formData.append("page_from", String(pageFrom));
  if (pageTo) formData.append("page_to", String(pageTo));
  return apiPost("/analysis/parse-file", formData, true); // true = multipart
}

// OCR 识别
async function ocrImage(file: File, engine: "aliyun" | "llm" = "aliyun") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("engine", engine);
  return apiPost("/analysis/ocr-image", formData, true);
}
```

---

## 5. 文件变更清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/app/services/ocr/aliyun_ocr.py` | 阿里云 OCR 客户端 |
| `backend/app/services/ocr/llm_vision.py` | LLM 视觉降级识别 |
| `backend/app/api/api_v1/endpoints/analysis_parse.py` | 文件解析和 OCR API 端点 |
| `frontend/src/components/FileUploadZone.tsx` | 文件上传区域组件 |
| `frontend/src/components/PageRangeSelector.tsx` | 页码范围选择器 |
| `frontend/src/components/OCRPreview.tsx` | OCR 结果预览组件 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `backend/requirements.txt` | 新增 `alibabacloud-ocr-api20210707` |
| `backend/app/core/config.py` | 新增阿里云 OCR 配置项 |
| `backend/app/api/api_v1/api.py` | 注册 analysis_parse 路由 |
| `frontend/src/app/analysis/page.tsx` | InputStep 中集成 FileUploadZone |
| `frontend/src/lib/api.ts` | 支持 multipart/form-data 请求 |
| `.env` | 新增阿里云 OCR 密钥配置 |

---

## 6. 配置项

```env
# 阿里云 OCR
ALIYUN_OCR_ACCESS_KEY_ID=
ALIYUN_OCR_ACCESS_KEY_SECRET=
ALIYUN_OCR_ENDPOINT=ocr-api.cn-hangzhou.aliyuncs.com
```

---

## 7. 错误处理

| 场景 | 处理 |
|------|------|
| 文件格式不支持 | 前端校验，提示"仅支持 PDF/Word/TXT/照片" |
| 文件超过 10MB | 前端校验，提示文件过大 |
| PDF 页码范围无效 | 前端校验，起始页 ≤ 结束页 |
| OCR 识别失败 | 提示用户重试或切换引擎 |
| 阿里云 API 不可用 | 自动降级到 LLM 视觉，提示用户 |
| 网络超时 | 提示重试 |

---

## 8. 后续扩展

- 支持更多文件格式（PPT、Excel）
- 批量上传多文件合并分析
- OCR 识别结果手动修正（框选区域重新识别）
- 识别历史缓存（避免重复识别同一张照片）
