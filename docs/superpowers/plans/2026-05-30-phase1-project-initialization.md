# 项目初始化与基础框架搭建 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建飞书项目管理系统的基础框架，包括后端FastAPI、前端Vue3、Docker配置和项目目录结构。

**Architecture:** 采用前后端分离架构，后端使用FastAPI提供RESTful API，前端使用Vue3+TypeScript构建SPA应用。使用Docker Compose实现一键部署，SQLite作为数据库。

**Tech Stack:** FastAPI 0.110+, Vue 3, TypeScript, Element Plus, Docker, SQLite, Pydantic v2

---

## File Structure Overview

```
feishu_project_manager/
├── backend/
│   ├── api/
│   │   └── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   └── vite-env.d.ts
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── Dockerfile
│   └── .dockerignore
├── docker/
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── .env.example
├── .gitignore
└── README.md
```

---

### Task 1: 创建后端基础目录结构

**Files:**
- Create: `backend/api/__init__.py`
- Create: `backend/core/__init__.py`
- Create: `backend/core/config.py`
- Create: `backend/main.py`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`

- [ ] **Step 1: 创建后端目录结构**

```bash
mkdir -p backend/api backend/core backend/db backend/models backend/schemas backend/services backend/utils backend/tests
```

- [ ] **Step 2: 创建空的__init__.py文件**

```bash
touch backend/api/__init__.py backend/core/__init__.py backend/db/__init__.py backend/models/__init__.py backend/schemas/__init__.py backend/services/__init__.py backend/utils/__init__.py
```

- [ ] **Step 3: 创建配置文件 backend/core/config.py**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    APP_NAME: str = "Feishu Project Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/feishu_pm.db"
    
    # JWT配置
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7
    
    # 飞书配置
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_VERIFICATION_TOKEN: str = ""
    FEISHU_ENCRYPT_KEY: str = ""
    
    # 系统配置
    TIMEZONE: str = "Asia/Shanghai"
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
```

- [ ] **Step 4: 创建FastAPI主入口 backend/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """健康检查接口"""
    return {
        "message": "Feishu Project Manager API",
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/api/v1/health")
async def health_check():
    """API健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 5: 创建依赖清单 backend/requirements.txt**

```txt
fastapi==0.110.0
uvicorn[standard]==0.27.1
sqlalchemy==2.0.27
alembic==1.13.1
pydantic==2.6.1
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
httpx==0.26.0
lark-oapi==1.2.16
openpyxl==3.1.2
apscheduler==3.10.4
pytest==8.0.0
pytest-asyncio==0.23.4
```

- [ ] **Step 6: 创建环境变量示例 backend/.env.example**

```env
# 应用配置
APP_NAME=Feishu Project Manager
APP_VERSION=1.0.0
DEBUG=True

# 数据库配置
DATABASE_URL=sqlite:///./data/feishu_pm.db

# JWT配置
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# 飞书配置
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_VERIFICATION_TOKEN=xxx
FEISHU_ENCRYPT_KEY=xxx

# 系统配置
TIMEZONE=Asia/Shanghai
LOG_LEVEL=INFO
```

- [ ] **Step 7: 测试后端启动**

```bash
cd backend
python -m pip install -r requirements.txt
python main.py
```

Expected: 服务启动在 http://0.0.0.0:8000，访问 http://localhost:8000 返回欢迎信息

- [ ] **Step 8: 提交后端基础代码**

```bash
git add backend/
git commit -m "feat(backend): initialize FastAPI project structure

- Add core configuration with Pydantic settings
- Add main.py with health check endpoints
- Add requirements.txt with all dependencies
- Add .env.example for environment variables"
```

---

### Task 2: 创建前端基础框架

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/vite-env.d.ts`

- [ ] **Step 1: 创建前端目录结构**

```bash
mkdir -p frontend/src/api frontend/src/assets frontend/src/components frontend/src/layouts frontend/src/router frontend/src/stores frontend/src/utils frontend/src/views frontend/public
```

- [ ] **Step 2: 创建 package.json**

```json
{
  "name": "feishu-project-manager-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx,.cts,.mts --fix --ignore-path .gitignore"
  },
  "dependencies": {
    "vue": "^3.4.15",
    "vue-router": "^4.2.5",
    "pinia": "^2.1.7",
    "element-plus": "^2.5.6",
    "axios": "^1.6.7",
    "echarts": "^5.4.3",
    "@element-plus/icons-vue": "^2.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.3",
    "typescript": "^5.3.3",
    "vite": "^5.0.12",
    "vue-tsc": "^1.8.27",
    "@types/node": "^20.11.16"
  }
}
```

- [ ] **Step 3: 创建 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 4: 创建 tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 5: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>飞书项目管理系统</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 6: 创建 src/main.ts**

```typescript
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'

const app = createApp(App)

app.use(ElementPlus)

app.mount('#app')
```

- [ ] **Step 7: 创建 src/App.vue**

```vue
<template>
  <div id="app">
    <el-container>
      <el-header>
        <h1>飞书项目管理系统</h1>
      </el-header>
      <el-main>
        <el-card>
          <template #header>
            <span>欢迎使用</span>
          </template>
          <p>系统正在初始化...</p>
          <el-button type="primary" @click="testApi">测试API连接</el-button>
          <p v-if="apiStatus">{{ apiStatus }}</p>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'

const apiStatus = ref('')

const testApi = async () => {
  try {
    const response = await axios.get('/api/v1/health')
    apiStatus.value = `API连接成功: ${JSON.stringify(response.data)}`
  } catch (error) {
    apiStatus.value = `API连接失败: ${error}`
  }
}
</script>

<style scoped>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.el-header {
  background-color: #3370ff;
  color: white;
  display: flex;
  align-items: center;
}

.el-header h1 {
  margin: 0;
  font-size: 20px;
}

.el-main {
  background-color: #f5f7fa;
  padding: 20px;
}
</style>
```

- [ ] **Step 8: 创建 src/vite-env.d.ts**

```typescript
/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
```

- [ ] **Step 9: 测试前端启动**

```bash
cd frontend
npm install
npm run dev
```

Expected: 前端启动在 http://localhost:3000，页面显示欢迎信息

- [ ] **Step 10: 提交前端基础代码**

```bash
git add frontend/
git commit -m "feat(frontend): initialize Vue3 project with Element Plus

- Add Vite configuration with proxy to backend
- Add TypeScript configuration
- Add Element Plus UI library
- Add basic App.vue with API test button"
```

---

### Task 3: 配置Docker部署

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `docker/docker-compose.yml`
- Create: `docker/nginx.conf`
- Create: `docker/.env.example`

- [ ] **Step 1: 创建后端Dockerfile backend/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 创建前端Dockerfile frontend/Dockerfile**

```dockerfile
# 构建阶段
FROM node:20-alpine as build

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm install

# 构建应用
COPY . .
RUN npm run build

# 生产阶段
FROM nginx:alpine

# 复制构建产物
COPY --from=build /app/dist /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 3: 创建前端nginx配置 frontend/nginx.conf**

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

- [ ] **Step 4: 创建Docker Compose配置 docker/docker-compose.yml**

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    container_name: feishu_pm_backend
    ports:
      - "8000:8000"
    volumes:
      - ../backend:/app
      - backend_data:/app/data
    env_file:
      - .env
    restart: unless-stopped
    networks:
      - feishu_pm_network

  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    container_name: feishu_pm_frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - feishu_pm_network

volumes:
  backend_data:

networks:
  feishu_pm_network:
    driver: bridge
```

- [ ] **Step 5: 创建Docker环境变量 docker/.env.example**

```env
# 应用配置
APP_NAME=Feishu Project Manager
APP_VERSION=1.0.0
DEBUG=False

# 数据库配置
DATABASE_URL=sqlite:///./data/feishu_pm.db

# JWT配置
JWT_SECRET_KEY=change-this-to-a-random-secret-key-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# 飞书配置
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_VERIFICATION_TOKEN=
FEISHU_ENCRYPT_KEY=

# 系统配置
TIMEZONE=Asia/Shanghai
LOG_LEVEL=INFO
```

- [ ] **Step 6: 测试Docker构建**

```bash
cd docker
cp .env.example .env
docker-compose build
```

Expected: 后端和前端镜像构建成功

- [ ] **Step 7: 测试Docker启动**

```bash
docker-compose up -d
```

Expected: 容器启动成功，访问 http://localhost 可以看到前端页面

- [ ] **Step 8: 提交Docker配置**

```bash
git add backend/Dockerfile frontend/Dockerfile frontend/nginx.conf docker/
git commit -m "feat(docker): add Docker and Docker Compose configuration

- Add backend Dockerfile with Python 3.11
- Add frontend Dockerfile with multi-stage build
- Add nginx configuration for frontend
- Add docker-compose.yml for one-click deployment
- Add .env.example for environment variables"
```

---

### Task 4: 创建项目文档

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `docs/deployment.md`

- [ ] **Step 1: 创建 README.md**

```markdown
# 飞书项目管理系统

一款面向小团队的轻量化中长期项目进度管理系统，深度集成飞书生态。

## 功能特点

- 项目里程碑跟踪
- 任务分配与状态更新
- 风险与问题管理
- 飞书机器人通知与智能跟催
- 事件时间线与历史追溯
- Excel导入导出与定期报表

## 技术栈

**后端**:
- FastAPI 0.110+
- SQLAlchemy 2.0+
- SQLite
- APScheduler

**前端**:
- Vue 3 + TypeScript
- Element Plus
- Pinia
- ECharts

## 快速开始

### 使用Docker（推荐）

1. 克隆仓库
```bash
git clone https://github.com/sptwalker/feishu_project_manager.git
cd feishu_project_manager
```

2. 配置环境变量
```bash
cd docker
cp .env.example .env
# 编辑.env文件，填写飞书配置
```

3. 启动服务
```bash
docker-compose up -d
```

4. 访问系统
- 前端: http://localhost
- 后端API文档: http://localhost:8000/docs

### 本地开发

**后端**:
```bash
cd backend
pip install -r requirements.txt
python main.py
```

**前端**:
```bash
cd frontend
npm install
npm run dev
```

## 飞书应用配置

1. 登录飞书开放平台: https://open.feishu.cn
2. 创建企业自建应用
3. 配置应用权限（获取用户信息、发送消息、访问多维表格）
4. 配置OAuth回调地址: `https://your-domain.com/api/v1/auth/feishu/callback`
5. 获取App ID、App Secret、Verification Token并填入.env文件

## 项目结构

```
feishu_project_manager/
├── backend/          # 后端FastAPI项目
├── frontend/         # 前端Vue3项目
├── docker/           # Docker配置
└── docs/             # 项目文档
```

## 开发规范

- 后端遵循PEP 8规范
- 前端遵循Vue 3官方风格指南
- Git提交遵循Conventional Commits规范

## 许可证

MIT License
```

- [ ] **Step 2: 创建 .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
dist/
.DS_Store

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Environment
.env
.env.local
.env.*.local

# Database
*.db
*.sqlite
*.sqlite3
data/

# Logs
*.log
logs/

# Docker
docker-compose.override.yml

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 3: 创建 docs/deployment.md**

```markdown
# 部署文档

## 生产环境部署

### 1. 服务器要求

- 操作系统: Ubuntu 20.04+ / CentOS 7+
- Docker: 20.10+
- Docker Compose: 2.0+
- 内存: 最低2GB，推荐4GB
- 磁盘: 最低10GB可用空间

### 2. 部署步骤

#### 2.1 安装Docker

```bash
# Ubuntu
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2.2 克隆项目

```bash
git clone https://github.com/sptwalker/feishu_project_manager.git
cd feishu_project_manager
```

#### 2.3 配置环境变量

```bash
cd docker
cp .env.example .env
vim .env
```

必须配置的变量:
- `JWT_SECRET_KEY`: 生成随机密钥
- `FEISHU_APP_ID`: 飞书应用ID
- `FEISHU_APP_SECRET`: 飞书应用密钥
- `FEISHU_VERIFICATION_TOKEN`: 飞书验证令牌

#### 2.4 启动服务

```bash
docker-compose up -d
```

#### 2.5 查看日志

```bash
docker-compose logs -f
```

### 3. 反向代理配置（可选）

如果需要使用域名访问，可以配置Nginx反向代理:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. 数据备份

```bash
# 备份SQLite数据库
docker exec feishu_pm_backend cp /app/data/feishu_pm.db /app/data/backup_$(date +%Y%m%d).db

# 复制到宿主机
docker cp feishu_pm_backend:/app/data/backup_$(date +%Y%m%d).db ./
```

### 5. 更新部署

```bash
git pull
cd docker
docker-compose down
docker-compose build
docker-compose up -d
```

## 故障排查

### 后端无法启动

1. 检查日志: `docker-compose logs backend`
2. 检查环境变量配置
3. 检查数据库文件权限

### 前端无法访问

1. 检查容器状态: `docker-compose ps`
2. 检查nginx配置
3. 检查后端API是否正常

### 飞书集成失败

1. 验证飞书应用配置
2. 检查回调地址是否正确
3. 查看后端日志中的飞书API调用错误
```

- [ ] **Step 4: 提交项目文档**

```bash
git add README.md .gitignore docs/deployment.md
git commit -m "docs: add project documentation

- Add README.md with quick start guide
- Add .gitignore for Python and Node
- Add deployment.md with production deployment guide"
```

---

### Task 5: 验证完整部署流程

**Files:**
- Test: All created files

- [ ] **Step 1: 清理环境**

```bash
cd docker
docker-compose down -v
```

- [ ] **Step 2: 完整部署测试**

```bash
# 从根目录开始
cd docker
cp .env.example .env
docker-compose build
docker-compose up -d
```

Expected: 所有容器启动成功

- [ ] **Step 3: 测试后端健康检查**

```bash
curl http://localhost:8000/api/v1/health
```

Expected: 返回 `{"status":"healthy"}`

- [ ] **Step 4: 测试前端访问**

打开浏览器访问 http://localhost

Expected: 看到"飞书项目管理系统"页面，点击"测试API连接"按钮能成功连接后端

- [ ] **Step 5: 检查容器状态**

```bash
docker-compose ps
```

Expected: backend和frontend容器都处于Up状态

- [ ] **Step 6: 查看日志确认无错误**

```bash
docker-compose logs
```

Expected: 无ERROR级别日志

- [ ] **Step 7: 创建最终提交**

```bash
git add -A
git commit -m "chore: complete phase 1 - project initialization

Phase 1 完成，包括:
- 后端FastAPI基础框架
- 前端Vue3基础框架
- Docker一键部署配置
- 项目文档

下一步: Phase 2 - 数据库模型与迁移系统"
```

- [ ] **Step 8: 推送到远程仓库**

```bash
git push origin main
```

---

## Self-Review Checklist

### 1. Spec Coverage

✅ 项目目录结构 - Task 1, 2
✅ 后端FastAPI框架 - Task 1
✅ 前端Vue3框架 - Task 2
✅ Docker配置 - Task 3
✅ 基础配置文件 - Task 1, 3
✅ 项目文档 - Task 4
✅ 部署验证 - Task 5

### 2. Placeholder Scan

✅ 无TBD或TODO
✅ 所有代码块完整
✅ 所有命令包含预期输出
✅ 无"类似Task N"的引用

### 3. Type Consistency

✅ Settings类在config.py中定义，在main.py中使用一致
✅ FastAPI app实例命名一致
✅ 环境变量命名在.env.example和config.py中一致

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-30-phase1-project-initialization.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
