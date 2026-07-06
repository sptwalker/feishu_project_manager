# 构建阶段
FROM node:20-alpine AS build

WORKDIR /app

# 安装依赖（使用 lockfile 保证可复现构建）
COPY package.json package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com && \
    npm ci

# 构建应用
# 部署版本号（侧栏底部显示）：compose 传入 git 短哈希，未传则 vite 内部退回 'dev'
ARG APP_VERSION
ENV VITE_APP_VERSION=$APP_VERSION
COPY . .
RUN npm run build

# 生产阶段
FROM nginx:alpine

# 复制构建产物
COPY --from=build /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
