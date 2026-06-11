# 构建阶段
FROM node:18-alpine AS builder

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖（使用 ci 确保版本一致）
RUN npm ci

# 复制应用代码
COPY . .

# 构建生产版本
RUN npm run build

# 生产阶段
FROM node:18-alpine

WORKDIR /app

# 创建非root用户
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

# 从builder阶段复制构建产物
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
COPY --from=builder /app/public ./public

# 切换到非root用户
USER nextjs

# 暴露端口
EXPOSE 3000

# 启动生产服务器
CMD ["npm", "start"]
