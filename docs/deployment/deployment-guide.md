# OutEye Edu 1.0 部署指南

## 适用范围

本指南描述 **当前真实可维护的部署口径**。当前推荐的唯一官方方式是：

> **Docker Compose + Nginx（Docker-first）**

如果你看到其他文档中仍有 `alembic upgrade head`、`create_admin.py` 或旧目录结构说明，请以本文件和 `docker-compose.yml` 为准。

---

## 1. 当前部署架构

```text
浏览器
  ↓
Nginx (:80)
  ├─ /      → Next.js frontend (:3000)
  └─ /api/  → FastAPI backend (:8000)

backend 还会连接：
- PostgreSQL
- Redis
- Qdrant
- OutEye-Wiki（挂载目录）
```

### 服务清单

| 服务 | 作用 | 默认暴露端口 |
|------|------|-------------|
| nginx | 统一入口与反向代理 | `80`, `443` |
| frontend | Next.js 生产服务 | `3000` |
| backend | FastAPI API | `8000` |
| qdrant | 向量检索 | `6333`, `6334` |
| postgres | 关系数据库 | 不对宿主机暴露 |
| redis | 缓存 / 限流 | 不对宿主机暴露 |

> 推荐通过 `http://localhost` 访问应用，而不是把 `3000` 端口当成唯一入口。生产构建下，前端默认依赖 Nginx 代理 `/api/`。

---

## 2. 目录前提

当前 Docker Compose 假设 `OutEye-Wiki` 与 `outeye-edu` 处于同级目录：

```text
outeye3.0/
├── OutEye-Wiki/
└── outeye-edu/
```

Compose 会把主机上的 `OutEye-Wiki` 目录挂载到 backend 容器内的 `/app/OutEye-Wiki`。

如果你的知识库不在默认位置，请在 `.env` 中修改：

```env
WIKI_HOST_PATH=../OutEye-Wiki
```

---

## 3. 环境变量契约

### 3.1 Docker-first：复制模板

在 `outeye-edu/` 目录下：

```bash
cp .env.example .env
```

Windows 可以直接复制 `.env.example` 为 `.env`。

### 3.2 必填项

至少填写以下变量：

```env
POSTGRES_PASSWORD=...
REDIS_PASSWORD=...
SECRET_KEY=...
JWT_SECRET_KEY=...
LLM_API_KEY=...
```

### 3.3 常用可调项

```env
WIKI_HOST_PATH=../OutEye-Wiki
NEXT_PUBLIC_API_URL=http://localhost
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
EMBEDDING_MODEL=bge-small-zh-v1.5
EMBEDDING_DIMENSION=512
QDRANT_COLLECTION=outeye_knowledge
LOG_LEVEL=INFO
LOG_FILE=logs/outeye.log
```

### 3.4 本地直跑补充变量

如果你不使用 Docker，而是单独启动 backend / frontend，请不要直接照搬 Docker-first 变量。

backend 直跑需要：

```env
DATABASE_URL=postgresql+asyncpg://outeye:password@localhost:5432/outeye_edu
REDIS_URL=redis://:password@localhost:6379/0
QDRANT_URL=http://localhost:6333
WIKI_DATA_PATH=../OutEye-Wiki
```

frontend 直跑需要：

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 4. Docker Compose 部署

### 4.1 启动服务

在 `outeye-edu/` 目录执行：

```bash
docker compose up -d --build
```

### 4.2 查看服务状态

```bash
docker compose ps
docker compose logs -f
```

### 4.3 访问入口

- 应用入口：`http://localhost`
- 前端容器直连：`http://localhost:3000`
- 后端 API：`http://localhost:8000`
- OpenAPI：`http://localhost:8000/docs`
- Qdrant：`http://localhost:6333`

---

## 5. 当前数据库策略

### 5.1 当前真实行为

当前项目**不依赖 Alembic**。启动 backend 时会执行：

1. `Base.metadata.create_all()` 自动建表
2. 启动期幂等补列逻辑（用于补充新增字段）

### 5.2 这意味着什么

- 不需要执行 `alembic upgrade head`
- 不需要运行 `create_admin.py`
- 当前更适合作为原型 / 演示环境
- 若未来进入多环境、多人协作和长期维护，再补正式迁移体系更合适

### 5.3 风险提示

这种方式适合当前阶段，但不适合高频 schema 变更的正式生产环境。

---

## 6. 最小可行验证链路

建议每次部署后至少执行以下验证。

### 6.1 后端单元测试

```bash
cd backend
pytest tests -q
```

### 6.2 前端构建验证

```bash
npm --prefix frontend run build
```

### 6.3 服务健康检查

```bash
curl http://localhost:8000/health
curl http://localhost/health
```

### 6.4 关键接口验证

#### 1）注册用户
```http
POST /api/v1/users/
```

#### 2）登录
```http
POST /api/v1/users/login
```

#### 3）白盒分析
```http
POST /api/v1/analysis/whitebox
Authorization: Bearer <token>
```

#### 4）Wiki 搜索
```http
GET /api/v1/wiki/search?query=krashen&max_results=5
```

#### 5）专家评审统计
```http
GET /api/v1/expert-review/stats
```

### 6.5 最小人工冒烟流程

1. 打开 `http://localhost`
2. 注册账号并登录
3. 打开“课文分析”页
4. 走通：
   - 文件解析 / OCR（任选）
   - 白盒分析
   - 双源检索
   - 教学方案生成
5. 打开“知识库”页，验证搜索与理论详情
6. 打开“专家评审”页，验证统计读取与提交评审

---

## 7. 本地开发启动（可选）

### 7.1 backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7.2 frontend

```bash
cd frontend
npm install
npm run dev
```

### 7.3 本地开发说明

- frontend 开发模式依赖 `frontend/.env.local` 中的 `NEXT_PUBLIC_API_URL=http://localhost:8000`
- backend 本地运行时请显式配置 `WIKI_DATA_PATH=../OutEye-Wiki`
- 本地开发可以绕过 Nginx，但 Docker-first 部署场景不建议绕过

---

## 8. 故障排除

### 8.1 Wiki 相关功能报错

先检查：
- 主机路径 `WIKI_HOST_PATH` 是否正确
- `OutEye-Wiki/` 是否存在
- backend 容器内是否成功挂载到 `/app/OutEye-Wiki`

### 8.2 前端页面能打开，但 API 请求失败

先检查：
- 是否通过 `http://localhost` 访问，而不是仅访问 `http://localhost:3000`
- `NEXT_PUBLIC_API_URL` 是否与当前访问入口一致
- Nginx 是否正常启动

### 8.3 RAG / OCR / 生成效果异常

先检查：
- `LLM_API_KEY` 是否有效
- Qdrant 服务是否健康
- OCR 相关第三方凭据是否已配置

### 8.4 数据库初始化异常

先检查：
- `POSTGRES_PASSWORD` 是否为空
- PostgreSQL 健康检查是否通过
- backend 日志中是否有建表 / 启动期补列错误

---

## 9. 生产化提醒

当前这套部署更适合：
- 比赛演示
- 内部试用
- 原型验证

如果你准备进入正式生产阶段，下一步优先项应该是：

1. 引入正式数据库迁移体系
2. 固化 CI 构建与验证流程
3. 收口前端 API 基址策略
4. 补齐更完整的集成测试与部署监控

---

**当前官方文档优先级**：`docker-compose.yml` > 本文件 > README > 历史申报材料
