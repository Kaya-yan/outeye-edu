# OutEye Edu 1.0 API 参考文档

## 说明

本文档是 **当前运行时 API 参考**，以 `backend/app/api/api_v1/` 下的真实路由为准。

- 推荐通过 Nginx 同源访问：`http://localhost/api/v1`
- 也可直接访问后端：`http://localhost:8000/api/v1`
- 历史申报材料中的旧接口命名，不再作为当前对接依据

## 认证方式

除特别说明外，受保护接口都需要：

```http
Authorization: Bearer <access_token>
```

获取 token 的标准流程：
1. `POST /users/` 注册
2. `POST /users/login` 登录
3. 在请求头中带上 Bearer Token

---

## 1. 健康检查

### GET /health/
基础健康检查。

**响应示例**
```json
{
  "status": "healthy",
  "service": "OutEye Edu API",
  "version": "1.0.0"
}
```

### GET /health/db
数据库健康检查。

---

## 2. 用户与认证

### POST /users/
注册用户。

**请求体**
```json
{
  "email": "teacher@example.com",
  "password": "password123",
  "full_name": "张老师",
  "institution": "某大学",
  "title": "副教授"
}
```

### POST /users/login
用户登录。

**请求体**
```json
{
  "email": "teacher@example.com",
  "password": "password123"
}
```

**响应示例**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 7200
}
```

### GET /users/me
获取当前用户信息（需要认证）。

### GET /users/
获取用户列表（需要认证）。

### GET /users/{user_id}
获取指定用户（需要认证）。

### PUT /users/{user_id}
更新当前用户信息（需要认证，仅允许更新自己）。

### DELETE /users/{user_id}
删除当前用户（需要认证，仅允许删除自己）。

---

## 3. 当前主链路：课文分析与教学方案生成

这是前端当前实际依赖的核心流程：

```text
文件解析 / OCR
   ↓
白盒分析
   ↓
双源检索（Wiki + RAG）
   ↓
教学方案生成
   ↓
教学方案修订 / 导出
```

### 3.1 POST /analysis/parse-file
上传并解析课文文件（需要认证）。

**Content-Type**: `multipart/form-data`

**表单字段**
- `file`: PDF / DOCX / TXT / MD
- `page_from`（可选，仅 PDF）
- `page_to`（可选，仅 PDF）

**响应示例**
```json
{
  "text": "parsed text...",
  "filename": "lesson.pdf",
  "total_pages": 12,
  "page_from": 1,
  "page_to": 3,
  "word_count": 860,
  "file_type": "pdf"
}
```

### 3.2 POST /analysis/ocr-image
上传图片并进行 OCR（需要认证）。

**Content-Type**: `multipart/form-data`

**表单字段**
- `file`: JPG / JPEG / PNG / WebP
- `engine`: `aliyun`（默认）或 `llm`

### 3.3 POST /analysis/whitebox
白盒分析主入口（需要认证）。

**请求体**
```json
{
  "text": "课文内容...",
  "title": "Language Learning Evolution",
  "student_level": "B1",
  "language": "en",
  "native_language": "zh",
  "course_type": "精读",
  "class_size": 30
}
```

**响应特征**
- `text_id`
- `text_level`
- `language`
- `vocabulary`
- `syntax`
- `discourse`
- `learner_gap`
- `enhancement_tags`
- `wiki_tags`
- `rag_tags`
- `teaching_tips`

> 若白盒分析失败，接口会尝试回退到旧分析引擎，并在返回结果中标记 `fallback_used`。

### 3.4 POST /analysis/retrieve
双源并行检索（需要认证）。

**请求体**
```json
{
  "wiki_tags": ["cognitive-load", "scaffolding"],
  "rag_tags": ["reading-strategy", "classroom-activity"],
  "enhancement_tags": ["high_academic_density"],
  "text_title": "Language Learning Evolution",
  "max_results": 3
}
```

**响应示例**
```json
{
  "wiki_results": [],
  "rag_results": [],
  "wiki_query_used": "...",
  "rag_query_used": "...",
  "retrieval_duration": 1.24,
  "wiki_count": 2,
  "rag_count": 3
}
```

### 3.5 POST /analysis/generate-plan
完整流水线：白盒分析 → 双源检索 → LLM 生成教学方案（需要认证）。

**请求体**
```json
{
  "text": "课文内容...",
  "title": "Language Learning Evolution",
  "student_level": "B1",
  "language": "en",
  "native_language": "zh",
  "course_type": "精读",
  "class_size": 30,
  "max_retrieval_results": 3
}
```

**响应特征**
- `text_title`
- `text_level`
- `student_level`
- `learner_gap`
- `enhancement_tags`
- `tag_labels`
- `teaching_plan`
- `sources`
- `retrieval_info`
- `generation_duration`
- `total_duration`
- `model`

### 3.6 POST /analysis/revise-plan
基于教师意见修订教学方案（需要认证）。

**请求体**
```json
{
  "original_plan": {
    "difficulty_overview": "...",
    "teaching_suggestions": ["..."],
    "activity_designs": [],
    "differentiation": "...",
    "theoretical_basis": "..."
  },
  "revision_instruction": "请减少课堂活动数量，强化分层任务",
  "text": "原始课文内容...",
  "title": "Language Learning Evolution",
  "student_level": "B1",
  "language": "en",
  "section_to_revise": "activities"
}
```

### 3.7 POST /analysis/export
导出教学方案（需要认证）。

**请求体**
```json
{
  "format": "pptx",
  "title": "教学方案",
  "plan": {
    "difficulty_overview": "...",
    "teaching_suggestions": ["..."],
    "activity_designs": [],
    "differentiation": "...",
    "theoretical_basis": "..."
  }
}
```

**支持格式**
- `pptx`
- `docx`
- `html`

### 3.8 POST /analysis/compare
教材对比分析（需要认证）。

**请求体**
```json
{
  "texts": [
    { "title": "课文 A", "text": "..." },
    { "title": "课文 B", "text": "..." }
  ],
  "student_level": "B1"
}
```

**约束**
- 最少 2 篇
- 最多 5 篇
- 每篇文本至少 10 个字符，前端实际建议至少 20

---

## 4. Wiki 知识库接口

这部分接口是当前知识库页面实际使用的接口。

### GET /wiki/tags
获取可用理论标签列表。

### GET /wiki/search?query=<关键词>&max_results=10
按关键词搜索 Wiki。

### GET /wiki/theory/{theory_name}
按理论名获取相关页面搜索结果。

### GET /wiki/theory/{theory_name}/network
获取理论关联网络。

### GET /wiki/page/{page_name}
获取单个 Wiki 页面详情。

### GET /wiki/statistics
获取 Wiki 统计信息。

### POST /wiki/refresh
刷新 Wiki 缓存。

> 当前前端主要使用：`/wiki/tags`、`/wiki/search`、`/wiki/theory/{theory_name}`。

---

## 5. 专家评审接口

### GET /expert-review/stats
获取评审统计（公开接口，前端首页与评审页使用）。

### POST /expert-review/submit
提交专家评审（需要认证）。

**请求体**
```json
{
  "plan_id": "lesson-plan-001",
  "reviewer_name": "李教授",
  "reviewer_title": "教授",
  "reviewer_institution": "某大学",
  "score_objective": 4,
  "score_activity": 5,
  "score_theory": 4,
  "score_differentiation": 4,
  "score_practicability": 5,
  "comments": "活动设计完整，理论支撑明确。",
  "suggestion": "建议增加低水平学生的替代任务。"
}
```

### GET /expert-review/list
获取评审列表（需要认证，可按 `plan_id` 过滤）。

---

## 6. RAG 知识库接口

### POST /rag/upload
直接上传文本内容并入库。

**请求体**
```json
{
  "title": "Krashen Notes",
  "content": "文档正文...",
  "metadata": { "source": "manual" }
}
```

### POST /rag/upload-file
上传文件并入库。

**Content-Type**: `multipart/form-data`

### POST /rag/query
RAG 检索问答。

**请求体**
```json
{
  "query": "Krashen 的输入假说是什么？",
  "method": "hybrid",
  "top_k": 5,
  "use_wiki": true,
  "filter_conditions": null
}
```

### POST /rag/query-with-wiki
Wiki + RAG 联合查询。

### GET /rag/stats
获取当前向量集合统计。

### DELETE /rag/documents/{doc_id}
删除指定文档及其向量分块。

### POST /rag/search-similar
按文本查找相似分块。

---

## 7. 用户反馈接口

### POST /feedback/
提交用户反馈（需要认证）。

### GET /feedback/my
获取当前用户自己的反馈列表（需要认证）。

### GET /feedback/stats
获取反馈统计。

### POST /feedback/satisfaction?rating=5&comment=...
提交满意度评分（需要认证）。

---

## 8. 其他模块

以下模块当前仍在后端中保留，但不是前端主链路的核心对接入口：

- `/analysis/analyze`
- `/analysis/generate-lesson-plan`
- `/analysis/analyze/lexical`
- `/analysis/analyze/syntactic`
- `/analysis/analyze/discourse`
- `/analysis/analyze/cognitive-load`
- `/projects/*`
- `/resources/*`
- `/knowledge/*`

如果你在做新对接，优先使用本文档前几节列出的当前主链路接口；只有在确认业务仍依赖旧模块时，再回看相应路由文件。

---

## 9. 速率限制与错误响应

### 速率限制
项目当前在路由层启用了限流依赖，具体限制以 `app/core/rate_limit.py` 为准。

### 通用错误格式
接口失败时通常返回：

```json
{
  "detail": "错误说明"
}
```

常见状态码：
- `400` 请求参数错误
- `401` 未登录或 token 无效
- `403` 权限不足
- `404` 资源不存在
- `413` 文件过大
- `422` 校验失败
- `429` 请求过于频繁
- `500` 服务器内部错误

---

## 10. 对接建议

- 做前端联调时，优先参考：
  - `frontend/src/app/analysis/page.tsx`
  - `frontend/src/app/knowledge/page.tsx`
  - `frontend/src/app/expert-review/page.tsx`
  - `frontend/src/lib/auth-context.tsx`
- 做部署联调时，优先参考：
  - `docker-compose.yml`
  - `docs/deployment/deployment-guide.md`
- 做接口核对时，优先参考：
  - `backend/app/api/api_v1/api.py`
  - `backend/app/api/api_v1/endpoints/`
