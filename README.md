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
