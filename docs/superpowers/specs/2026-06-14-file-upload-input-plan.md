# 课文输入体验优化 — 实现计划

> 基于设计规格：`docs/superpowers/specs/2026-06-14-file-upload-input-design.md`

## 任务清单

### 任务 1：后端 OCR 服务

**新增文件：**
- `backend/app/services/ocr/__init__.py`
- `backend/app/services/ocr/aliyun_ocr.py`
- `backend/app/services/ocr/llm_vision.py`

**做什么：**

1. `aliyun_ocr.py`：
   - 使用 `alibabacloud-ocr-api20210707` SDK
   - `AliyunOCR` 类，`recognize(image_bytes) -> {text, confidence}`
   - 调用 `RecognizeGeneral` 通用文字识别接口
   - 处理异常返回

2. `llm_vision.py`：
   - 使用已有的 OpenAI SDK（DeepSeek/Mimo）
   - `recognize_with_llm(image_base64) -> {text, engine}`
   - 将图片 base64 作为多模态输入，prompt 要求识别文字
   - 复用已有的 LLM 配置（`LLM_API_KEY`, `LLM_BASE_URL` 等）

3. `__init__.py`：
   - 导出 `AliyunOCR`, `recognize_with_llm`

**验证：** 单元测试传入测试图片，确认返回识别文本。

---

### 任务 2：后端文件解析 API 端点

**新增文件：**
- `backend/app/api/api_v1/endpoints/analysis_parse.py`

**做什么：**

1. `POST /analysis/parse-file`：
   - 接收 `UploadFile` + `page_from` + `page_to`
   - 验证文件类型（.pdf/.docx/.txt/.md）和大小（10MB）
   - 保存到临时文件
   - 根据文件类型调用已有 `DocumentParser.parse_file()`
   - PDF 特殊处理：使用 PyPDF2 按页码范围提取
   - 返回 `{ text, filename, total_pages, page_from, page_to, word_count, file_type }`
   - 清理临时文件

2. `POST /analysis/ocr-image`：
   - 接收 `UploadFile` + `engine`（aliyun/llm）
   - 验证图片格式（.jpg/.png/.webp）和大小
   - 调用对应的 OCR 服务
   - 返回 `{ text, confidence, engine, word_count }`

**修改文件：**
- `backend/app/api/api_v1/api.py`：注册新路由

**验证：** 用 curl 测试两个端点，传入测试文件。

---

### 任务 3：后端配置和依赖

**修改文件：**
- `backend/requirements.txt`：新增 `alibabacloud-ocr-api20210707`
- `backend/app/core/config.py`：新增阿里云 OCR 配置项
- `.env`：新增 `ALIYUN_OCR_ACCESS_KEY_ID`、`ALIYUN_OCR_ACCESS_KEY_SECRET`、`ALIYUN_OCR_ENDPOINT`

**验证：** `pip install` 成功，配置可读取。

---

### 任务 4：前端 API 工具函数

**修改文件：**
- `frontend/src/lib/api.ts`

**做什么：**
- 新增 `apiUpload(url, formData)` 函数，支持 `multipart/form-data`
- 复用已有的 token 和 base URL 逻辑

**验证：** 函数可正确发送 FormData 请求。

---

### 任务 5：前端 FileUploadZone 组件

**新增文件：**
- `frontend/src/components/FileUploadZone.tsx`

**做什么：**
- 拖拽上传区域（虚线框 + 图标 + 提示文字）
- 点击选择文件（`<input type="file">` 隐藏）
- 文件类型前端校验
- 上传状态显示（loading）
- 上传成功后：
  - 文本文件 → 直接返回解析文本
  - PDF → 显示 PageRangeSelector
  - 图片 → 显示 OCRPreview
- 回调 `onTextExtracted(text)` 通知父组件

**验证：** 组件渲染正常，拖拽和点击上传可触发。

---

### 任务 6：前端 PageRangeSelector 组件

**新增文件：**
- `frontend/src/components/PageRangeSelector.tsx`

**做什么：**
- 显示文件名和总页数
- 范围模式下拉："全部页面" / "自定义范围"
- 选择"自定义范围"后显示两个下拉框（起始页/结束页）
- 页面预览条：一排小方块代表每页，选中范围高亮
- 起始页 ≤ 结束页自动校验
- "确认提取" 按钮，调用 `parseFile(file, pageFrom, pageTo)`

**验证：** 选择不同范围，确认回调传递正确的页码。

---

### 任务 7：前端 OCRPreview 组件

**新增文件：**
- `frontend/src/components/OCRPreview.tsx`

**做什么：**
- 显示识别文本（可滚动区域）
- 识别引擎标签
- "确认使用" 按钮 → 回调 `onConfirm(text)`
- "重新识别" 按钮 → 重新调用 OCR
- "切换引擎" 按钮 → 降级到 LLM 视觉

**验证：** 识别结果正确显示，按钮回调正常。

---

### 任务 8：集成到分析页面

**修改文件：**
- `frontend/src/app/analysis/page.tsx`

**做什么：**
- 在 InputStep 中，标题输入上方插入 `<FileUploadZone />`
- `onTextExtracted` 回调中调用 `setText(text)` 填入编辑器
- 自动更新标题（如果文件名可作为标题）
- 上传后自动计算词数，确保按钮可用

**验证：** 完整流程：上传文件 → 文本填入编辑器 → 点击分析。

---

## 执行顺序

```
任务 1 (OCR 服务) + 任务 4 (前端 API)  ←  无依赖，可并行
    ↓
任务 2 (文件解析端点) + 任务 5 (FileUploadZone)  ←  依赖任务 1/4
    ↓
任务 3 (配置和依赖)  ←  依赖任务 1
    ↓
任务 6 (PageRangeSelector) + 任务 7 (OCRPreview)  ←  依赖任务 5
    ↓
任务 8 (集成到分析页面)  ←  依赖任务 5/6/7
```

## 文件变更清单

| 操作 | 文件 |
|------|------|
| 新建 | `backend/app/services/ocr/__init__.py` |
| 新建 | `backend/app/services/ocr/aliyun_ocr.py` |
| 新建 | `backend/app/services/ocr/llm_vision.py` |
| 新建 | `backend/app/api/api_v1/endpoints/analysis_parse.py` |
| 新建 | `frontend/src/components/FileUploadZone.tsx` |
| 新建 | `frontend/src/components/PageRangeSelector.tsx` |
| 新建 | `frontend/src/components/OCRPreview.tsx` |
| 修改 | `backend/requirements.txt` |
| 修改 | `backend/app/core/config.py` |
| 修改 | `backend/app/api/api_v1/api.py` |
| 修改 | `frontend/src/lib/api.ts` |
| 修改 | `frontend/src/app/analysis/page.tsx` |
| 修改 | `.env` |
