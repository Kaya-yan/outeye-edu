# OutEye Edu 1.0 API 参考文档

## 概述

OutEye Edu 1.0 提供 RESTful API 接口，用于智能教研操作系统的各项功能。

**基础URL**: `http://localhost:8000/api/v1`

**认证方式**: Bearer Token (JWT)

---

## 1. 健康检查 API

### GET /health

检查系统健康状态。

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2026-06-11T12:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "qdrant": "healthy"
  }
}
```

---

## 2. 用户管理 API

### POST /users/register

用户注册。

**请求体**:
```json
{
  "username": "teacher1",
  "email": "teacher@example.com",
  "password": "securepassword",
  "role": "teacher",
  "full_name": "张老师"
}
```

**响应**: 201 Created

### POST /users/login

用户登录。

**请求体**:
```json
{
  "username": "teacher1",
  "password": "securepassword"
}
```

**响应**:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### GET /users/me

获取当前用户信息（需要认证）。

**响应**:
```json
{
  "id": "uuid",
  "username": "teacher1",
  "email": "teacher@example.com",
  "role": "teacher",
  "full_name": "张老师"
}
```

---

## 3. 智能分析 API

### POST /analysis/analyze

课文综合分析。

**请求体**:
```json
{
  "text": "课文内容...",
  "student_level": "B1",
  "analysis_types": ["lexical", "syntactic", "discourse", "cognitive_load"]
}
```

**响应**:
```json
{
  "analysis_id": "uuid",
  "lexical": {
    "total_words": 250,
    "unique_words": 180,
    "vocabulary_richness": 0.72,
    "academic_word_count": 15,
    "cefr_distribution": {
      "A1": 45,
      "A2": 38,
      "B1": 42,
      "B2": 30,
      "C1": 15,
      "C2": 10
    },
    "difficulty_score": 3.5
  },
  "syntactic": {
    "total_sentences": 15,
    "avg_sentence_length": 16.7,
    "flesch_kincaid_grade": 8.5,
    "flesch_reading_ease": 65.2,
    "sentence_types": {
      "simple": 5,
      "compound": 4,
      "complex": 6
    }
  },
  "discourse": {
    "paragraph_count": 4,
    "coherence_score": 0.78,
    "genre_type": "expository",
    "cohesion_devices": {
      "reference": 12,
      "conjunction": 8,
      "lexical_cohesion": 15
    }
  },
  "cognitive_load": {
    "intrinsic_load": 6.2,
    "extraneous_load": 2.1,
    "germane_load": 4.5,
    "total_load": 12.8,
    "overload_risk": "medium",
    "recommendations": [
      "建议增加预习环节",
      "提供词汇支持"
    ]
  },
  "teaching_suggestions": [
    "建议采用任务型教学法",
    "分组讨论促进互动"
  ]
}
```

### POST /analysis/analyze/lexical

词汇维度分析。

**请求体**:
```json
{
  "text": "课文内容...",
  "student_level": "B1"
}
```

### POST /analysis/analyze/syntactic

句法维度分析。

**请求体**:
```json
{
  "text": "课文内容..."
}
```

### POST /analysis/analyze/discourse

语篇维度分析。

**请求体**:
```json
{
  "text": "课文内容..."
}
```

### POST /analysis/analyze/cognitive-load

认知负荷分析。

**请求体**:
```json
{
  "text": "课文内容...",
  "student_level": "B1"
}
```

### POST /analysis/generate-lesson-plan

教案自动生成。

**请求体**:
```json
{
  "text": "课文内容...",
  "student_level": "B1",
  "duration_minutes": 45,
  "class_size": 30
}
```

**响应**:
```json
{
  "lesson_plan_id": "uuid",
  "title": "Lesson Plan: ...",
  "objectives": [
    {
      "description": "学生能够...",
      "bloom_level": "understand",
      "measurable": true
    }
  ],
  "activities": [
    {
      "name": "导入活动",
      "duration": 10,
      "type": "warm-up",
      "description": "..."
    }
  ],
  "differentiation": {
    "advanced": "...",
    "intermediate": "...",
    "beginner": "..."
  },
  "assessment": {
    "formative": "...",
    "summative": "..."
  }
}
```

---

## 4. RAG 知识库 API

### POST /rag/upload

上传文档到知识库。

**请求体**: multipart/form-data

- `file`: 文档文件（PDF, Word, Markdown, HTML, TXT）
- `metadata`: JSON 格式的元数据

**响应**:
```json
{
  "document_id": "uuid",
  "filename": "document.pdf",
  "chunks_count": 25,
  "status": "indexed"
}
```

### POST /rag/query

知识库查询。

**请求体**:
```json
{
  "query": "Krashen的输入假说是什么？",
  "top_k": 5,
  "method": "hybrid"
}
```

**响应**:
```json
{
  "query_id": "uuid",
  "results": [
    {
      "content": "...",
      "source": "krashen-i-plus-1.md",
      "score": 0.92,
      "metadata": {
        "theory": "Krashen i+1",
        "section": "核心概念"
      }
    }
  ],
  "answer": "根据知识库，Krashen的输入假说认为..."
}
```

### POST /rag/query-with-wiki

Wiki增强查询。

**请求体**:
```json
{
  "query": "如何将认知负荷理论应用于教学设计？",
  "use_wiki": true,
  "use_rag": true
}
```

**响应**:
```json
{
  "query_id": "uuid",
  "wiki_results": [...],
  "rag_results": [...],
  "synthesized_answer": "...",
  "sources": [...]
}
```

### GET /rag/stats

获取知识库统计信息。

**响应**:
```json
{
  "total_documents": 150,
  "total_chunks": 2500,
  "collection_name": "outeye_knowledge",
  "vector_size": 1024
}
```

---

## 5. Wiki 知识库 API

### GET /wiki/entities

获取所有理论实体列表。

**响应**:
```json
{
  "entities": [
    {
      "id": "krashen-i-plus-1",
      "name": "Krashen i+1 输入假说",
      "category": "语言习得理论",
      "tags": ["SLA", "input", "comprehension"]
    }
  ]
}
```

### GET /wiki/entities/{entity_id}

获取理论实体详情。

**响应**:
```json
{
  "id": "krashen-i-plus-1",
  "name": "Krashen i+1 输入假说",
  "content": "...",
  "related_theories": [...],
  "engineering_mapping": {...},
  "prompt_templates": [...]
}
```

### GET /wiki/search

搜索Wiki内容。

**查询参数**:
- `q`: 搜索关键词
- `category`: 分类过滤
- `tags`: 标签过滤

### GET /wiki/graph

获取知识图谱数据。

**响应**:
```json
{
  "nodes": [...],
  "edges": [...],
  "clusters": [...]
}
```

---

## 6. 资源推荐 API

### POST /resources/recommend

获取教学资源推荐。

**请求体**:
```json
{
  "topic": "阅读教学",
  "text_content": "课文内容...",
  "student_level": "B1",
  "resource_types": ["literature", "courseware", "exercises"]
}
```

**响应**:
```json
{
  "recommendations": {
    "literature": [
      {
        "title": "...",
        "authors": ["..."],
        "relevance_score": 0.85,
        "abstract": "..."
      }
    ],
    "courseware": [...],
    "exercises": [...]
  }
}
```

---

## 错误响应

所有API在出错时返回标准错误格式：

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "请求参数错误",
    "details": {
      "field": "text",
      "reason": "文本内容不能为空"
    }
  }
}
```

**常见错误码**:
- `400`: 请求参数错误
- `401`: 未认证
- `403`: 权限不足
- `404`: 资源不存在
- `422`: 验证错误
- `500`: 服务器内部错误

---

## 速率限制

- 普通用户：100 请求/分钟
- 高级用户：500 请求/分钟
- 管理员：无限制

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2026-06-11 | 初始版本 |
