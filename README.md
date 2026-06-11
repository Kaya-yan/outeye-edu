# OutEye Edu 1.0

面向外国语言文学一流学科建设的智能教研操作系统

## 项目结构

```
outeye-edu/
├── backend/          # FastAPI后端
│   ├── app/          # 应用代码
│   ├── tests/        # 测试代码
│   ├── alembic/      # 数据库迁移
│   └── scripts/      # 工具脚本
├── frontend/         # Next.js前端
│   ├── src/          # 源代码
│   ├── public/       # 静态资源
│   ├── components/   # 组件库
│   ├── pages/        # 页面
│   └── styles/       # 样式
├── wiki/             # OutEye-Wiki知识库
├── docker/           # Docker配置
│   ├── nginx/        # Nginx配置
│   ├── postgres/     # PostgreSQL配置
│   ├── redis/        # Redis配置
│   └── qdrant/       # Qdrant配置
└── docs/             # 项目文档
    ├── api/          # API文档
    ├── architecture/ # 架构文档
    ├── deployment/   # 部署文档
    └── user-guide/   # 用户手册
```

## 技术栈

- **后端**：FastAPI + Python 3.11+
- **前端**：Next.js 14 + React 18 + TailwindCSS
- **数据库**：PostgreSQL 15 + Redis + Qdrant
- **AI模型**：DeepSeek API + bge-large-zh-v1.5
- **部署**：Docker Compose + Nginx

## 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd outeye-edu
```

### 2. 启动开发环境
```bash
# 启动所有服务
docker-compose up -d

# 启动后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 启动前端
cd frontend
npm install
npm run dev
```

### 3. 访问应用
- 前端：http://localhost:3000
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

## 核心功能

1. **智能课文分析引擎**：六维分析报告
2. **教案自动生成系统**：基于理论的教学设计
3. **教学资源推荐模块**：RAG驱动的文献推荐
4. **学情分析与评估系统**：学习效果跟踪

## 开发计划

- 阶段1：需求分析与架构设计 ✅
- 阶段2：技术栈选型与项目初始化 🔄
- 阶段3：LLM Wiki知识库构建
- 阶段4：RAG系统实现
- 阶段5：核心功能开发
- 阶段6：前端界面开发
- 阶段7：系统集成与测试
- 阶段8：部署与交付

## 许可证

MIT License

---

**项目**：OutEye Edu 1.0 - 揭榜挂帅专项赛
**维护者**：赵琰
**创建日期**：2026-06-11