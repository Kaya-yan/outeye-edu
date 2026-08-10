# OutEye Edu 1.0 开发日志

## 项目信息

- **项目名称**：OutEye Edu 1.0（分析驱动双源检索增强型智能教研操作系统）
- **项目负责人**：赵琰
- **GitHub**：https://github.com/Kaya-yan/outeye-edu
- **服务器**：阿里云轻量应用服务器，青岛地域，2核4G，Ubuntu 22.04
- **公网 IP**：118.190.132.184

---

## 阶段一：需求分析与架构设计（2026-06-01 ~ 2026-06-08）

### 2026-06-01
- 收到挑战杯"揭榜挂帅"专项赛赛题文档
- 分析项目方案文档（项目方案啊0601.docx）和核心技术方案（项目核心技术完整方案加长.docx）
- 明确四大核心痛点：教学资源分散、理论难以落地、个性化不足、评估低效

### 2026-06-02 ~ 2026-06-04
- 梳理 12 大语言学理论工程化需求：
  - 语言难度评估层：Lexile Framework、Flesch-Kincaid、CEFR、AWL
  - 二语习得与认知层：Krashen i+1、认知负荷理论、Noticing 假说
  - 教学设计与思维层：Bloom 分类学、ZPD/支架理论、Paul & Elder 批判性思维
  - 语篇与修辞分析层：体裁分析(Swales)、RST 修辞结构、主位推进理论
- 确定 RAG + LLM Wiki 混合架构方案
- 设计三层架构：知识编译层（Wiki）→ 灵活检索层（RAG）→ 应用层

### 2026-06-05 ~ 2026-06-08
- 完成系统整体架构设计
- 技术栈选型：FastAPI + Next.js 14 + PostgreSQL + Redis + Qdrant
- 设计数据库 Schema（12 张核心表）
- 制定 16 周开发计划

**产出物**：
- `DEVELOPMENT_PLAN.md` — 16 周全栈开发计划
- `项目方案啊0601.docx` — 项目方案
- `项目核心技术完整方案加长.docx` — 核心技术方案

---

## 阶段二：项目初始化（2026-06-08 ~ 2026-06-10）

### 2026-06-08
- 初始化项目目录结构
- 创建后端 FastAPI 主应用、配置文件、数据库配置
- 创建前端 Next.js 项目、TailwindCSS 配置
- 编写 docker-compose.yml、Dockerfile、Nginx 配置
- 编写 PostgreSQL 初始化脚本（init.sql）

### 2026-06-09 ~ 2026-06-10
- 完成后端核心配置模块：config.py、database.py、cache.py、security.py、rate_limit.py
- 完成 API 端点骨架：health、users、projects、analysis、resources、knowledge、wiki、rag、feedback
- 完成前端页面骨架：首页、登录、注册、分析、资源、知识库、项目管理
- 配置开发环境（本地 PostgreSQL、Redis、Qdrant）

**产出物**：
- `outeye-edu/backend/` — 后端项目结构
- `outeye-edu/frontend/` — 前端项目结构
- `outeye-edu/docker/` — Docker 配置
- `outeye-edu/.env.example` — 环境变量模板

---

## 阶段三：LLM Wiki 知识库构建（2026-06-08 ~ 2026-06-11）

### 2026-06-08 ~ 2026-06-09
- 创建 OutEye-Wiki 知识库目录结构（Obsidian 兼容格式）
- 编写 SCHEMA.md 知识库规范
- 创建第一个理论实体页：Krashen i+1 输入假说

### 2026-06-10 ~ 2026-06-11
- 完成全部 12 个理论实体页（每个从 ~800B 扩展到 15-28KB）：
  - krashen-i-plus-1.md（6.8KB）
  - bloom-taxonomy.md（14.3KB）
  - cognitive-load-theory.md（17.2KB）
  - cefr.md（20.3KB）
  - lexical-framework.md（17.4KB）
  - flesch-kincaid.md（14.6KB）
  - noticing-hypothesis.md（20.3KB）
  - zone-of-proximal-development.md（24.3KB）
  - genre-analysis.md（24.1KB）
  - rhetorical-structure-theory.md（22.2KB）
  - thematic-progress.md（25.1KB）
  - paul-elder-critical-thinking.md（28.8KB）
- 完成 6 个核心概念页：RAG、LLM Wiki、自适应学习、话语分析、DAG、文化传播
- 建立知识图谱关联（Wikilinks 交叉引用）
- 实现 Wiki 解析器（parser.py）和查询服务（query.py）

**产出物**：
- `OutEye-Wiki/` — 完整知识库（12 实体页 + 6 概念页，约 25 万字符）
- `backend/app/services/wiki/parser.py` — Wiki 解析器
- `backend/app/services/wiki/query.py` — Wiki 查询服务

---

## 阶段四：RAG 系统实现（2026-06-11 ~ 2026-06-12）

### 2026-06-11
- 实现文档解析器（document_parser.py）：支持 PDF、Word、Markdown、HTML、TXT
- 实现 Embedding 服务（embedding.py）：集成 bge-small-zh-v1.5 模型
- 实现向量存储（vector_store.py）：集成 Qdrant，支持 HNSW 索引

### 2026-06-12
- 实现混合检索器（retriever.py）：稠密检索 + 稀疏检索 + RRF 融合
- 实现 RAG 生成器（generator.py）：集成 DeepSeek API
- 实现 Wiki 与 RAG 协同查询机制
- 编写 RAG 相关单元测试

**产出物**：
- `backend/app/services/rag/document_parser.py`
- `backend/app/services/rag/embedding.py`
- `backend/app/services/rag/vector_store.py`
- `backend/app/services/rag/retriever.py`
- `backend/app/services/rag/generator.py`

---

## 阶段五：核心功能开发（2026-06-11 ~ 2026-06-14）

### 2026-06-11
- 实现词汇分析器（lexical_analyzer.py，476 行）：CEFR 分布、AWL 识别、Lexile 值、TTR
- 实现句法分析器（syntactic_analyzer.py，251 行）：Flesch-Kincaid、句子类型分类、从句密度
- 实现语篇分析器（discourse_analyzer.py，294 行）：连贯性、体裁识别、衔接手段、主位推进
- 实现认知负荷分析器（cognitive_load_analyzer.py，383 行）：Sweller 三维负荷、过载风险
- 实现文本分析引擎主编排器（text_analyzer.py，295 行）：六维分析整合

### 2026-06-11 ~ 2026-06-12
- 实现教案生成器（lesson_plan_generator.py，452 行）：基于 Bloom 分类学的教学设计
- 实现资源推荐器（resource_recommender.py，252 行）：RAG 驱动推荐
- 实现学习分析模块（learning_analytics.py，397 行）：学习效果跟踪

### 2026-06-12 ~ 2026-06-14
- 实现白盒分析器（whitebox_analyzer.py，1507 行）：透明分析，可解释结果
- 实现融合生成器（fusion_generator.py，489 行）
- 实现双检索器（dual_retriever.py，271 行）
- 实现检索规划器（retrieval_planner.py，121 行）
- 实现计划修订器（plan_reviser.py，233 行）
- 实现标签生成器（tag_generator.py，161 行）
- 实现导出服务（export_service.py，400 行）
- 实现语言检测器（language_detector.py，57 行）
- 实现多语言分词器（multilingual_tokenizer.py，344 行）

**产出物**：
- `backend/app/services/analysis/` — 17 个分析服务文件，共约 6,000 行代码

---

## 阶段六：前端界面开发（2026-06-12 ~ 2026-06-16）

### 2026-06-12
- 设计 Landing Page（page.tsx，344 行）：Hero、统计数据、功能介绍、架构概览、12 理论展示
- 实现导航栏组件（Navbar.tsx，142 行）

### 2026-06-13 ~ 2026-06-14
- 实现课文分析页面（analysis/page.tsx，868 行）：文件上传、参数配置、六维报告展示
- 实现文本对比页面（compare/page.tsx，310 行）
- 实现项目管理页面（projects/page.tsx，209 行）
- 实现资源检索页面（resources/page.tsx，357 行）
- 实现知识库浏览页面（knowledge/page.tsx，308 行）

### 2026-06-14 ~ 2026-06-16
- 实现登录/注册页面（login/、register/）
- 实现专家评审页面（expert-review/page.tsx，317 行）
- 实现文件上传组件（FileUploadZone.tsx，283 行）
- 实现 OCR 预览组件（OCRPreview.tsx，75 行）
- 实现页码选择器（PageRangeSelector.tsx，131 行）
- 实现教案展示组件（TeachingPlanView.tsx，438 行）
- 实现白盒结果组件（WhiteboxResults.tsx，332 行）
- 实现富文本编辑器（TiptapEditor.tsx，127 行）
- 实现图表组件：RadarChart、CefrBarChart、DifficultWordsChart、ReadabilityGauge
- 实现认证上下文（auth-context.tsx）和 API 客户端（api.ts）

**产出物**：
- `frontend/src/app/` — 9 个页面
- `frontend/src/components/` — 11 个组件 + 4 个图表组件
- `frontend/src/lib/` — 3 个工具模块

---

## 阶段七：系统集成与补充开发（2026-06-14 ~ 2026-06-17）

### 2026-06-14
- 实现 OCR 服务：阿里云 OCR（aliyun_ocr.py）和 LLM Vision（llm_vision.py）
- 实现数据清理服务（data_cleanup.py，148 行）：定时清理过期数据
- 实现用户行为追踪（user_tracker.py，227 行）

### 2026-06-15 ~ 2026-06-16
- 前后端联调
- 修复 API 接口兼容性问题
- 完善错误处理和日志记录
- 编写单元测试（test_analysis.py、test_rag_wiki_integration.py 等）

### 2026-06-17
- 全面代码审计，修复关键后端/前端问题
- 第一次 Git 提交（Initial commit: OutEye Edu 1.0）
- 第二次 Git 提交（Fix critical backend/frontend issues）

**产出物**：
- `PROJECT_SUMMARY.md` — 项目完成总结
- `docs/challenge-cup/project-report.md` — 挑战杯项目报告
- 完整的 API 文档、用户手册、部署指南

---

## 阶段八：GitHub 推送与服务器部署（2026-06-23）

### 2026-06-23 — 代码准备
- 更新 `.gitignore`：排除 demo 文件、开发工具目录、过程文件
- 通过 GitHub Desktop 推送全部代码到 https://github.com/Kaya-yan/outeye-edu

### 2026-06-23 — 服务器部署
- 购买阿里云轻量应用服务器（2核4G，青岛，Ubuntu 22.04）
- 安装 Docker，配置 Docker 国内镜像源
- 克隆代码到服务器 `/opt/outeye-edu`
- 配置 `.env` 生产环境变量
- 创建 Swap 分区（2G）

### 2026-06-23 — 部署问题修复

#### 问题 1：后端 Dockerfile apt-get 超时
- **原因**：Docker 容器内无法访问 deb.debian.org
- **修复**：在 apt-get 前添加 `sed` 替换为阿里云镜像源

#### 问题 2：pip 无法从 PyPI 下载包
- **原因**：Docker 容器内无法访问 PyPI 官方源
- **修复**：添加 `pip config set global.index-url` 为阿里云 PyPI 镜像

#### 问题 3：qdrant 健康检查失败
- **原因**：qdrant 镜像内无 curl/wget，健康检查命令不存在
- **修复**：移除 qdrant healthcheck，后端依赖改为 `condition: service_started`

#### 问题 4：Docker Hub 拉取超时
- **原因**：国内网络无法访问 Docker Hub
- **修复**：所有基础镜像切换为阿里云 ACR（registry.cn-hangzhou.aliyuncs.com）
  - backend/Dockerfile：python:3.11-slim → ACR 镜像
  - frontend/Dockerfile：node:18-alpine → ACR 镜像
  - docker-compose.yml：postgres、redis、nginx → ACR 镜像
  - qdrant：尝试 ACR，不行则本地 docker save/load 传输

**待解决问题**：
- qdrant 第三方镜像在阿里云 ACR 上可能不存在，需要本地传输
- 前端 npm 依赖安装可能需要配置国内 npm 镜像源

---

## 项目统计

| 指标 | 数据 |
|------|------|
| 开发周期 | 2026-06-01 ~ 2026-06-23 |
| 后端 Python 文件 | 31 个，约 9,557 行 |
| 前端 TSX/TS 文件 | 25 个，约 5,054 行 |
| Wiki 知识库 | 18 个 Markdown 文件，约 25 万字符 |
| 总代码行数 | 约 117,500+ 行 |
| Git 提交次数 | 2 次（初始提交 + 修复提交） |
| Docker 容器数 | 6 个（PostgreSQL + Redis + Qdrant + Backend + Frontend + Nginx） |
| API 端点数 | 12 组 |
| 前端页面数 | 9 个 |
| 理论工程化 | 12 个语言学理论 |

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户界面层                              │
│           (Next.js 14 + React 18 + TailwindCSS)             │
├─────────────────────────────────────────────────────────────┤
│                      API 网关层                              │
│                   (FastAPI + Python 3.11+)                   │
├───────────┬───────────┬───────────┬───────────┬─────────────┤
│ 分析引擎  │  RAG 引擎 │ Wiki 引擎 │ 推荐引擎  │  用户引擎   │
├───────────┴───────────┴───────────┴───────────┴─────────────┤
│                      数据存储层                              │
├───────────┬───────────┬───────────┬───────────┬─────────────┤
│PostgreSQL │   Redis   │  Qdrant   │LLM Wiki  │   文件存储   │
└───────────┴───────────┴───────────┴───────────┴─────────────┘
```

---

**最后更新**：2026-06-23
**维护者**：赵琰
