# OutEye Edu 1.0

面向外国语言文学一流学科建设的智能教研操作系统。

## 当前定位

OutEye Edu 当前是一个**可演示、可继续迭代的工程原型**，核心链路已经覆盖：

- 用户注册 / 登录
- 课文白盒分析
- Wiki + RAG 双源检索
- 教学方案生成 / 修订 / 导出
- 教材对比分析
- 专家评审
- Wiki 理论检索
- 用户反馈采集

## 真相源与文档分层

为避免历史文档与当前实现漂移，当前项目按下面的优先级理解：

### 一级真相源（当前运行以此为准）
- 运行配置：`backend/app/core/config.py`
- API 路由：`backend/app/api/api_v1/`
- Docker 编排：`docker-compose.yml`
- 当前部署说明：`docs/deployment/deployment-guide.md`
- 当前 API 参考：`docs/api/api-reference.md`

### 历史/申报材料（保留，但不作为当前运行说明）
- `PROJECT_SUMMARY.md`
- `docs/challenge-cup/`
- 根目录的阶段性规划与进度文件

## 项目结构

```text
outeye3.0/
├── OutEye-Wiki/                  # LLM Wiki 知识库（与 outeye-edu 同级）
└── outeye-edu/
    ├── backend/                  # FastAPI 后端
    │   ├── app/
    │   │   ├── api/
    │   │   ├── core/
    │   │   ├── models/
    │   │   ├── services/
    │   │   └── utils/
    │   ├── tests/
    │   ├── Dockerfile
    │   └── requirements.txt
    ├── frontend/                 # Next.js 14 前端（App Router）
    │   ├── src/
    │   │   ├── app/
    │   │   ├── components/
    │   │   └── lib/
    │   ├── Dockerfile
    │   └── package.json
    ├── docker/
    │   ├── nginx/
    │   └── postgres/
    ├── docs/
    │   ├── api/
    │   ├── deployment/
    │   ├── user-guide/
    │   └── challenge-cup/
    ├── docker-compose.yml
    ├── .env.example
    └── README.md
```

## 官方运行方式

### Docker-first（推荐，当前唯一官方口径）

1. 确保目录结构中存在同级知识库目录：`../OutEye-Wiki`
2. 复制环境变量模板：
   ```bash
   cp .env.example .env
   ```
   Windows 可手动复制 `.env.example` 为 `.env`
3. 填写 `.env` 中的必填项：
   - `POSTGRES_PASSWORD`
   - `REDIS_PASSWORD`
   - `SECRET_KEY`
   - `JWT_SECRET_KEY`
   - `LLM_API_KEY`
4. 启动服务：
   ```bash
   docker compose up -d --build
   ```
5. 访问系统：
   - **应用入口（推荐）**：`http://localhost`
   - 前端容器直连：`http://localhost:3000`
   - 后端 API：`http://localhost:8000`
   - OpenAPI：`http://localhost:8000/docs`
   - Qdrant：`http://localhost:6333`

> 注意：生产构建下，前端页面默认依赖 Nginx 转发 `/api/`，因此 Docker Compose 场景下请优先通过 `http://localhost` 访问，而不是把 `3000` 端口当作唯一入口。

## 本地开发方式（可选）

适合前后端分开调试，但不作为当前官方部署口径。

### 后端
在 `backend/.env` 中至少配置：

```env
DATABASE_URL=postgresql+asyncpg://outeye:password@localhost:5432/outeye_edu
REDIS_URL=redis://:password@localhost:6379/0
QDRANT_URL=http://localhost:6333
WIKI_DATA_PATH=../OutEye-Wiki
SECRET_KEY=...
JWT_SECRET_KEY=...
LLM_API_KEY=...
```

启动：

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端
在 `frontend/.env.local` 中配置：

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

启动：

```bash
cd frontend
npm install
npm run dev
```

## 当前数据库策略

当前项目处于原型期，数据库初始化采用：

- `Base.metadata.create_all()` 自动建表
- 启动时执行幂等补列逻辑

这意味着：
- **当前运行不依赖 Alembic**
- 部署时不需要执行 `alembic upgrade head`
- 后续若进入长期维护阶段，再补正式迁移体系更合适

## 最小验证建议

### 后端测试
```bash
cd backend
pytest tests -q
```

### 前端构建
```bash
npm --prefix frontend run build
```

### Docker 验证
```bash
docker compose up -d --build
curl http://localhost:8000/health
```

### 关键链路人工验证
1. 打开 `http://localhost`
2. 注册并登录
3. 进入课文分析页，执行：
   - 文件解析或 OCR
   - 白盒分析
   - 双源检索
   - 生成教学方案
4. 打开知识库页验证 Wiki 搜索
5. 打开专家评审页验证统计接口

## 已知约束

- Docker Compose 依赖同级 `OutEye-Wiki/` 目录；没有知识库目录时，Wiki 相关功能无法正常工作
- 前端生产构建默认依赖反向代理处理 `/api/` 路径
- 当前数据库策略适合原型阶段，不适合复杂多环境迁移管理
- OCR、LLM 与 RAG 效果依赖外部服务与模型配置

## 相关文档

- API 参考：`docs/api/api-reference.md`
- 部署指南：`docs/deployment/deployment-guide.md`
- 用户手册：`docs/user-guide/user-manual.md`
- 挑战杯材料：`docs/challenge-cup/`

---

**项目名称**：OutEye Edu 1.0  
**项目负责人**：赵琰  
**当前维护方向**：工程收口优先于新功能扩展
