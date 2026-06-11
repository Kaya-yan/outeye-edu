# OutEye Edu 1.0 部署指南

## 目录

1. [部署要求](#部署要求)
2. [环境准备](#环境准备)
3. [Docker 部署](#docker-部署)
4. [手动部署](#手动部署)
5. [生产环境配置](#生产环境配置)
6. [监控与维护](#监控与维护)
7. [故障排除](#故障排除)

---

## 部署要求

### 硬件要求

**最低配置**：
- CPU：4 核
- 内存：8 GB
- 存储：50 GB SSD
- 网络：100 Mbps

**推荐配置**：
- CPU：8 核
- 内存：16 GB
- 存储：100 GB SSD
- 网络：1 Gbps

### 软件要求

- **操作系统**：Ubuntu 22.04 LTS / CentOS 8 / Windows Server 2022
- **Docker**：24.0+
- **Docker Compose**：2.20+
- **Node.js**：18+（前端构建）
- **Python**：3.11+（后端运行）

---

## 环境准备

### 1. 安装 Docker

#### Ubuntu/Debian

```bash
# 更新包索引
sudo apt-get update

# 安装依赖
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加 Docker 官方 GPG 密钥
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 设置仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER

# 重新登录以使组更改生效
```

#### CentOS/RHEL

```bash
# 安装依赖
sudo yum install -y yum-utils

# 添加 Docker 仓库
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 安装 Docker Engine
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER
```

#### Windows

1. 下载 Docker Desktop：https://www.docker.com/products/docker-desktop
2. 运行安装程序
3. 重启计算机
4. 启动 Docker Desktop

### 2. 验证 Docker 安装

```bash
docker --version
docker compose version
docker run hello-world
```

### 3. 安装 Git

```bash
# Ubuntu/Debian
sudo apt-get install -y git

# CentOS/RHEL
sudo yum install -y git

# Windows
# 下载 Git for Windows: https://git-scm.com/download/win
```

---

## Docker 部署

### 1. 克隆项目

```bash
git clone <repository-url>
cd outeye-edu
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下变量：

```env
# 数据库配置
POSTGRES_DB=outeye_edu
POSTGRES_USER=outeye
POSTGRES_PASSWORD=your_secure_password

# Redis 配置
REDIS_PASSWORD=your_redis_password

# 应用配置
APP_NAME=OutEye Edu
APP_VERSION=1.0.0
DEBUG=false
SECRET_KEY=your_secret_key_at_least_32_chars

# AI 模型配置
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_API_URL=https://api.deepseek.com

# Embedding 模型配置
EMBEDDING_MODEL=bge-large-zh-v1.5
EMBEDDING_DEVICE=cpu

# 向量数据库配置
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=outeye_knowledge

# 前端配置
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=OutEye Edu
```

### 3. 启动服务

```bash
# 构建并启动所有服务
docker compose up -d --build

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 4. 初始化数据库

```bash
# 等待 PostgreSQL 启动
sleep 10

# 运行数据库迁移
docker compose exec backend python -m alembic upgrade head

# 创建管理员用户
docker compose exec backend python scripts/create_admin.py
```

### 5. 访问应用

- **前端**：http://localhost:3000
- **后端 API**：http://localhost:8000
- **API 文档**：http://localhost:8000/docs
- **Qdrant 控制台**：http://localhost:6333/dashboard

---

## 手动部署

### 1. 后端部署

#### 1.1 创建虚拟环境

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

#### 1.2 安装依赖

```bash
pip install -r requirements.txt
```

#### 1.3 配置环境变量

创建 `backend/.env` 文件：

```env
# 数据库
DATABASE_URL=postgresql://outeye:password@localhost:5432/outeye_edu

# Redis
REDIS_URL=redis://:password@localhost:6379/0

# 应用
APP_NAME=OutEye Edu
DEBUG=false
SECRET_KEY=your_secret_key

# AI 模型
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_API_URL=https://api.deepseek.com

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

#### 1.4 初始化数据库

```bash
# 创建数据库
createdb outeye_edu

# 运行迁移
python -m alembic upgrade head

# 创建管理员
python scripts/create_admin.py
```

#### 1.5 启动后端

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 2. 前端部署

#### 2.1 安装依赖

```bash
cd frontend
npm install
```

#### 2.2 配置环境变量

创建 `frontend/.env.local` 文件：

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=OutEye Edu
```

#### 2.3 构建生产版本

```bash
npm run build
```

#### 2.4 启动前端

```bash
# 开发模式
npm run dev

# 生产模式
npm start
```

### 3. 数据库部署

#### 3.1 安装 PostgreSQL

```bash
# Ubuntu/Debian
sudo apt-get install -y postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install -y postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### 3.2 创建数据库和用户

```bash
sudo -u postgres psql

CREATE USER outeye WITH PASSWORD 'your_password';
CREATE DATABASE outeye_edu OWNER outeye;
GRANT ALL PRIVILEGES ON DATABASE outeye_edu TO outeye;
\q
```

### 4. Redis 部署

```bash
# Ubuntu/Debian
sudo apt-get install -y redis-server

# 启动 Redis
sudo systemctl start redis
sudo systemctl enable redis

# 设置密码
sudo redis-cli CONFIG SET requirepass "your_password"
```

### 5. Qdrant 部署

```bash
# 使用 Docker
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

### 6. Nginx 配置

创建 `/etc/nginx/sites-available/outeye-edu`：

```nginx
server {
    listen 80;
    server_name your_domain.com;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # 静态文件
    location /static/ {
        alias /var/www/outeye-edu/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/outeye-edu /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 生产环境配置

### 1. SSL/TLS 配置

使用 Let's Encrypt 获取免费 SSL 证书：

```bash
# 安装 Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your_domain.com

# 自动续期
sudo crontab -e
# 添加：0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. 域名配置

1. 在域名注册商处添加 A 记录，指向服务器 IP
2. 等待 DNS 生效（通常 5-30 分钟）
3. 更新 Nginx 配置中的 `server_name`

### 3. 防火墙配置

```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 4. 数据库优化

编辑 PostgreSQL 配置 `/etc/postgresql/15/main/postgresql.conf`：

```conf
# 内存配置
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 64MB
maintenance_work_mem = 1GB

# 连接配置
max_connections = 200

# WAL 配置
wal_buffers = 64MB
checkpoint_completion_target = 0.9

# 日志配置
log_min_duration_statement = 1000
log_checkpoints = on
log_connections = on
log_disconnections = on
```

重启 PostgreSQL：

```bash
sudo systemctl restart postgresql
```

### 5. Redis 优化

编辑 Redis 配置 `/etc/redis/redis.conf`：

```conf
# 内存配置
maxmemory 4gb
maxmemory-policy allkeys-lru

# 持久化配置
save 900 1
save 300 10
save 60 10000

# 连接配置
timeout 300
tcp-keepalive 60
```

重启 Redis：

```bash
sudo systemctl restart redis
```

### 6. 环境变量生产配置

创建生产环境 `.env` 文件：

```env
# 应用配置
APP_NAME=OutEye Edu
APP_VERSION=1.0.0
DEBUG=false
SECRET_KEY=<generate-strong-key>

# 数据库（使用强密码）
POSTGRES_DB=outeye_edu
POSTGRES_USER=outeye
POSTGRES_PASSWORD=<strong-password>
DATABASE_URL=postgresql://outeye:<strong-password>@localhost:5432/outeye_edu

# Redis（使用强密码）
REDIS_PASSWORD=<strong-password>
REDIS_URL=redis://:<strong-password>@localhost:6379/0

# AI 模型
DEEPSEEK_API_KEY=<your-api-key>
DEEPSEEK_API_URL=https://api.deepseek.com

# 向量数据库
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=outeye_knowledge

# 前端
NEXT_PUBLIC_API_URL=https://your_domain.com
NEXT_PUBLIC_APP_NAME=OutEye Edu

# 日志
LOG_LEVEL=INFO
LOG_FILE=/var/log/outeye-edu/app.log

# 监控
SENTRY_DSN=<your-sentry-dsn>
```

---

## 监控与维护

### 1. 日志管理

#### 应用日志

```bash
# 查看后端日志
tail -f /var/log/outeye-edu/app.log

# 查看 Docker 日志
docker compose logs -f backend
docker compose logs -f frontend
```

#### 日志轮转

创建 `/etc/logrotate.d/outeye-edu`：

```
/var/log/outeye-edu/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload nginx
    endscript
}
```

### 2. 数据库备份

#### 自动备份脚本

创建 `scripts/backup.sh`：

```bash
#!/bin/bash

BACKUP_DIR="/var/backups/outeye-edu"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份 PostgreSQL
pg_dump -U outeye outeye_edu | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# 备份 Redis
redis-cli -a $REDIS_PASSWORD BGSAVE
cp /var/lib/redis/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# 备份 Qdrant
curl -X POST "http://localhost:6333/collections/outeye_knowledge/snapshots" \
  -H "Content-Type: application/json" \
  -d '{}'
curl -o $BACKUP_DIR/qdrant_$DATE.snapshot \
  "http://localhost:6333/collections/outeye_knowledge/snapshots/latest"

# 删除旧备份
find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

设置定时任务：

```bash
chmod +x scripts/backup.sh

# 每天凌晨 2 点备份
crontab -e
0 2 * * * /path/to/outeye-edu/scripts/backup.sh >> /var/log/outeye-edu/backup.log 2>&1
```

### 3. 监控工具

#### 使用 Docker Stats

```bash
# 查看容器资源使用
docker stats

# 持续监控
watch -n 5 docker stats
```

#### 使用 Prometheus + Grafana

1. 安装 Prometheus：

```bash
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

2. 安装 Grafana：

```bash
docker run -d \
  --name grafana \
  -p 3001:3000 \
  grafana/grafana
```

3. 配置监控目标

### 4. 性能优化

#### 应用层优化

1. **启用 Gzip 压缩**（Nginx）：
```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
```

2. **启用缓存**（Nginx）：
```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=outeye_cache:10m max_size=1g inactive=60m use_temp_path=off;
```

3. **数据库连接池**：
```python
# backend/app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=1800
)
```

#### 系统层优化

1. **增加文件描述符限制**：
```bash
# /etc/security/limits.conf
* soft nofile 65535
* hard nofile 65535
```

2. **优化内核参数**：
```bash
# /etc/sysctl.conf
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
```

---

## 故障排除

### 1. 服务无法启动

#### 检查日志

```bash
# 查看 Docker 日志
docker compose logs

# 查看特定服务日志
docker compose logs backend
docker compose logs frontend
docker compose logs postgres
```

#### 检查端口占用

```bash
# 检查端口占用
netstat -tulpn | grep :8000
netstat -tulpn | grep :3000
netstat -tulpn | grep :5432

# 杀死占用端口的进程
kill -9 <PID>
```

#### 检查磁盘空间

```bash
df -h
du -sh /var/lib/docker/
```

### 2. 数据库连接失败

#### 检查 PostgreSQL 状态

```bash
sudo systemctl status postgresql
sudo systemctl restart postgresql
```

#### 检查连接配置

```bash
# 测试连接
psql -U outeye -d outeye_edu -h localhost

# 检查 pg_hba.conf
sudo nano /etc/postgresql/15/main/pg_hba.conf
```

### 3. 向量数据库连接失败

#### 检查 Qdrant 状态

```bash
docker compose ps qdrant
docker compose logs qdrant

# 手动启动 Qdrant
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```

#### 测试 Qdrant 连接

```bash
curl http://localhost:6333/health
curl http://localhost:6333/collections
```

### 4. AI 模型调用失败

#### 检查 API 密钥

```bash
# 测试 DeepSeek API
curl -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"test"}]}'
```

#### 检查网络连接

```bash
ping api.deepseek.com
curl -I https://api.deepseek.com
```

### 5. 前端无法访问

#### 检查 Next.js 状态

```bash
# 查看进程
ps aux | grep next

# 检查端口
netstat -tulpn | grep :3000

# 重新构建
cd frontend
npm run build
npm start
```

#### 检查 Nginx 配置

```bash
sudo nginx -t
sudo systemctl restart nginx
```

### 6. 性能问题

#### 检查资源使用

```bash
# CPU 和内存
top
htop

# 磁盘 I/O
iostat -x 1

# 网络
iftop
```

#### 优化建议

1. **增加服务器资源**：CPU、内存、存储
2. **启用缓存**：Redis、Nginx 缓存
3. **数据库优化**：索引、查询优化
4. **负载均衡**：多实例部署
5. **CDN 加速**：静态资源 CDN

---

## 回滚操作

### Docker 回滚

```bash
# 停止当前服务
docker compose down

# 使用之前的镜像
docker compose up -d --build

# 或使用备份的镜像
docker load < backup_image.tar
docker compose up -d
```

### 数据库回滚

```bash
# 恢复 PostgreSQL 备份
gunzip < /var/backups/outeye-edu/postgres_20260611_020000.sql.gz | psql -U outeye outeye_edu

# 恢复 Redis 备份
sudo systemctl stop redis
cp /var/backups/outeye-edu/redis_20260611_020000.rdb /var/lib/redis/dump.rdb
sudo systemctl start redis
```

---

## 联系支持

如遇到无法解决的问题，请联系技术支持：

- **邮箱**：support@outeye-edu.com
- **电话**：400-xxx-xxxx
- **在线文档**：https://docs.outeye-edu.com

---

**版本**：1.0.0
**更新日期**：2026-06-11
