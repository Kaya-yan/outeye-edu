# OutEye Edu 1.0 启动指南

## 你需要做什么（按顺序执行）

### 第一步：安装必要的软件

#### 1. 安装 Python 3.11+
- 下载地址：https://www.python.org/downloads/
- **重要**：安装时勾选 "Add Python to PATH"
- 安装完成后，打开命令提示符（CMD）输入 `python --version` 验证

#### 2. 安装 Node.js 18+
- 下载地址：https://nodejs.org/
- 选择 LTS（长期支持版）
- 安装完成后，打开命令提示符输入 `node --version` 验证

#### 3. 安装 Git（可选，如果需要版本控制）
- 下载地址：https://git-scm.com/downloads

---

### 第二步：启动后端服务

#### 方法一：使用启动脚本（推荐）
1. 双击运行 `outeye-edu/start-backend.bat`
2. 等待脚本自动完成以下操作：
   - 创建 Python 虚拟环境
   - 安装所有依赖
   - 启动后端服务
3. 看到以下信息表示启动成功：
   ```
   [信息] 启动后端服务...
   [信息] API 文档: http://localhost:8000/docs
   ```
4. **保持此窗口打开**，不要关闭

#### 方法二：手动启动
1. 打开命令提示符（CMD）
2. 执行以下命令：
   ```bash
   cd C:\Users\ht\Documents\outeye3.0\outeye-edu\backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

### 第三步：启动前端服务

#### 方法一：使用启动脚本（推荐）
1. **新开一个命令提示符窗口**（不要关闭后端窗口）
2. 双击运行 `outeye-edu/start-frontend.bat`
3. 等待脚本自动完成以下操作：
   - 安装前端依赖
   - 启动开发服务器
4. 看到以下信息表示启动成功：
   ```
   [信息] 启动前端开发服务器...
   [信息] 访问地址: http://localhost:3000
   ```

#### 方法二：手动启动
1. **新开一个命令提示符窗口**
2. 执行以下命令：
   ```bash
   cd C:\Users\ht\Documents\outeye3.0\outeye-edu\frontend
   npm install
   npm run dev
   ```

---

### 第四步：访问系统

1. 打开浏览器（推荐 Chrome 或 Edge）
2. 访问：**http://localhost:3000**
3. 你将看到 OutEye Edu 1.0 的主界面

---

## 验证系统是否正常运行

### 检查后端
- 访问：http://localhost:8000/docs
- 应该看到 Swagger API 文档页面
- 点击 "健康检查" → "执行"，应该返回 `{"status": "healthy"}`

### 检查前端
- 访问：http://localhost:3000
- 应该看到 OutEye Edu 的欢迎页面
- 尝试点击各个功能模块

---

## 常见问题及解决

### 问题 1：Python 未找到
**错误信息**：`[错误] 未找到 Python`
**解决方法**：
1. 重新安装 Python，确保勾选 "Add Python to PATH"
2. 或者手动添加 Python 到系统环境变量

### 问题 2：Node.js 未找到
**错误信息**：`[错误] 未找到 Node.js`
**解决方法**：
1. 重新安装 Node.js
2. 安装完成后重启命令提示符

### 问题 3：端口被占用
**错误信息**：`[Errno 10048] 通常每个套接字地址只允许使用一次`
**解决方法**：
1. 关闭占用端口的程序
2. 或者修改端口号（需要修改配置文件）

### 问题 4：依赖安装失败
**错误信息**：`pip install` 或 `npm install` 失败
**解决方法**：
1. 检查网络连接
2. 尝试使用国内镜像源：
   - Python: `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
   - Node.js: `npm install --registry=https://registry.npmmirror.com`

### 问题 5：数据库连接失败
**错误信息**：`could not connect to server`
**解决方法**：
1. 检查 `.env` 文件中的数据库配置
2. 确保 Neon 数据库服务正常
3. 检查网络连接

---

## 项目文件说明

```
outeye-edu/
├── .env                    # 环境变量配置（已配置好）
├── .env.example            # 环境变量模板
├── start-backend.bat       # 后端启动脚本
├── start-frontend.bat      # 前端启动脚本
├── backend/                # 后端代码
│   ├── app/                # 应用代码
│   ├── requirements.txt    # Python 依赖
│   └── Dockerfile          # Docker 配置
├── frontend/               # 前端代码
│   ├── src/                # 源代码
│   ├── package.json        # Node.js 依赖
│   └── Dockerfile          # Docker 配置
├── docker-compose.yml      # Docker 编排配置
└── docs/                   # 项目文档
```

---

## 环境变量配置说明

`.env` 文件需要配置以下内容（参考 `.env.example`）：

### 必需配置
- `SECRET_KEY` - 应用密钥（至少32字符）
- `JWT_SECRET_KEY` - JWT 签名密钥（至少32字符）
- `DATABASE_URL` - 数据库连接字符串
- `LLM_API_KEY` - AI 模型 API 密钥

### 可选配置
- `REDIS_URL` - Redis 连接地址（默认 localhost:6379）
- `QDRANT_URL` - Qdrant 向量数据库地址（默认 localhost:6333）
- `NEXT_PUBLIC_API_URL` - 后端 API 地址（默认 http://localhost:8000）

---

## 下一步：部署到线上（可选）

如果需要将系统部署到线上供更多用户测试，可以参考：
- `docs/deployment/deployment-guide.md` - 详细部署指南
- 推荐使用 Railway 或 Render 进行部署

---

## 技术支持

如遇到问题，请检查：
1. 是否按照上述步骤正确安装了 Python 和 Node.js
2. 是否正确配置了 `.env` 文件
3. 是否保持了后端和前端服务的运行
4. 查看日志文件：`backend/logs/outeye.log`

---

**最后更新**：2026-06-11
**版本**：OutEye Edu 1.0
