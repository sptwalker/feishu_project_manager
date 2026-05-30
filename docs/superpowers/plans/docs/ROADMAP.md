# 飞书项目管理系统 - 开发路线图

**项目名称**: feishu_project_manager  
**更新日期**: 2026-05-30

---

## 项目概述

一款面向小团队（10-50人）的轻量化中长期项目进度管理系统，深度集成飞书生态。

**核心特性**:
- 轻量化部署，快速上手
- 飞书深度集成（OAuth登录、机器人通知、多维表格同步）
- 完整的事件溯源和历史追踪
- 项目里程碑和任务管理
- 风险预警和智能跟催

---

## 开发阶段

### ✅ Phase 1: 项目初始化（已完成）

**状态**: 已完成  
**提交**: 初始化提交

**完成内容**:
- 项目目录结构创建
- Git 仓库初始化
- 基础配置文件

---

### ✅ Phase 2: 数据库模型与迁移系统（已完成）

**状态**: 已完成  
**计划文档**: `docs/superpowers/plans/2026-05-30-phase2-database-models.md`  
**提交数量**: 11 commits  
**最后提交**: f7c4bce

**完成内容**:
1. **数据库基础设施**
   - SQLAlchemy 2.0 引擎和会话管理
   - 支持 SQLite（开发）和 PostgreSQL（生产）
   - 数据库初始化函数

2. **核心数据模型**
   - User 模型（飞书用户集成、角色管理）
   - Project 模型（状态、紧急程度、完成度）
   - Task 模型（优先级、父子关系、依赖）
   - Event 模型（审计追踪、变更历史）
   - Risk 模型（风险管理、状态跟踪）

3. **数据库迁移**
   - Alembic 配置和初始化
   - 初始迁移脚本（3250137362e7）
   - 枚举值修复（lowercase）

**数据库表结构**:
- `users` - 用户表
- `projects` - 项目表
- `tasks` - 任务表
- `events` - 事件表
- `risks` - 风险表
- `alembic_version` - 迁移版本控制

**技术栈**:
- SQLAlchemy 2.0+
- Alembic 1.13+
- Pydantic v2
- SQLite/PostgreSQL

---

### 🚧 Phase 3: 飞书 OAuth 登录与 JWT 认证系统（进行中）

**状态**: 计划已完成，待实现  
**计划文档**: 
- `docs/superpowers/plans/2026-05-30-phase3-authentication-system.md`
- `docs/superpowers/plans/2026-05-30-phase3-code-supplement.md`

**目标**:
实现完整的飞书 OAuth 2.0 登录流程和 JWT 令牌认证系统

**任务列表**:
1. ✅ Task 1: 配置飞书应用和安全密钥
2. ✅ Task 2: 实现 JWT 安全工具
3. ✅ Task 3: 创建认证相关 Schema
4. ✅ Task 4: 实现飞书 API 客户端
5. ✅ Task 5: 实现认证服务层
6. ✅ Task 6: 实现 FastAPI 依赖注入
7. ✅ Task 7: 实现认证 API 路由
8. ✅ Task 8: 注册路由到主应用
9. ⏳ Task 9: 验证和完成

**核心功能**:
- 飞书 OAuth 2.0 登录
- JWT access token 和 refresh token
- 用户注册和信息同步
- 基于角色的权限控制（RBAC）
- Token 刷新机制

**技术栈**:
- FastAPI 0.110+
- python-jose[cryptography]
- passlib[bcrypt]
- httpx
- Pydantic v2

**API 端点**:
- `GET /api/v1/auth/feishu/login` - 飞书登录跳转
- `GET /api/v1/auth/feishu/callback` - OAuth 回调
- `POST /api/v1/auth/refresh` - 刷新 token
- `POST /api/v1/auth/logout` - 退出登录

---

### 📋 Phase 4: 项目管理 API（计划中）

**状态**: 待规划  
**预计任务数**: 8-10 tasks

**目标**:
实现项目的 CRUD 操作和相关业务逻辑

**计划功能**:
1. 项目 CRUD 接口
2. 项目列表（筛选、排序、分页）
3. 项目详情和统计
4. 项目时间线
5. 项目状态流转
6. 项目成员管理

**API 端点**:
- `GET /api/v1/projects` - 获取项目列表
- `POST /api/v1/projects` - 创建项目
- `GET /api/v1/projects/{id}` - 获取项目详情
- `PUT /api/v1/projects/{id}` - 更新项目
- `DELETE /api/v1/projects/{id}` - 删除项目
- `GET /api/v1/projects/{id}/timeline` - 项目时间线
- `GET /api/v1/projects/{id}/statistics` - 项目统计

---

### ✅ Phase 5: 任务管理 API（已完成）

**状态**: 已完成
**实现方式**: 参照 Phase 4 同构模式（schema → service → permissions → api → tests）

**目标**:
实现任务的 CRUD 操作和父子层级管理（任务依赖关系不在本阶段范围内）

**完成功能**:
1. ✅ 任务 CRUD 接口
2. ✅ 任务列表（按状态/优先级/负责人/父任务过滤，分页）
3. ✅ 子任务管理（父子层级）
4. ✅ 任务权限控制（管理员 / 任务负责人 / 所属项目所有者）
5. ✅ 测试覆盖（schema/service/api/permissions，共 41 个用例）

**API 端点**:
- `GET /api/v1/projects/{project_id}/tasks` - 获取任务列表
- `POST /api/v1/projects/{project_id}/tasks` - 创建任务
- `GET /api/v1/tasks/{id}` - 获取任务详情
- `PUT /api/v1/tasks/{id}` - 更新任务
- `DELETE /api/v1/tasks/{id}` - 删除任务
- `GET /api/v1/tasks/{id}/subtasks` - 获取子任务列表
- `POST /api/v1/tasks/{id}/subtasks` - 创建子任务

**相关文件**:
- `backend/schemas/task.py`
- `backend/services/task_service.py`
- `backend/api/v1/tasks.py`
- `backend/core/permissions.py`（新增任务权限方法）
- `backend/tests/test_task_*.py`

---

### ✅ Phase 6: 风险管理 API（已完成）

**状态**: 已完成
**实现方式**: 参照 Phase 4/5 同构模式（schema → service → permissions → api → tests）

**目标**:
实现风险的登记、跟踪与状态流转

**完成功能**:
1. ✅ 风险 CRUD 接口
2. ✅ 风险列表（按状态/负责人过滤，分页）
3. ✅ 风险状态流转（open / monitoring / resolved）
4. ✅ 风险权限控制（管理员 / 风险负责人 / 所属项目所有者；负责人可空）
5. ✅ 测试覆盖（schema/service/api/permissions，共 31 个用例）

**API 端点**:
- `GET /api/v1/projects/{project_id}/risks` - 获取风险列表
- `POST /api/v1/projects/{project_id}/risks` - 创建风险
- `GET /api/v1/risks/{id}` - 获取风险详情
- `PUT /api/v1/risks/{id}` - 更新风险
- `DELETE /api/v1/risks/{id}` - 删除风险

**相关文件**:
- `backend/schemas/risk.py`
- `backend/services/risk_service.py`
- `backend/api/v1/risks.py`
- `backend/core/permissions.py`（新增风险权限方法）
- `backend/tests/test_risk_*.py`

---

### 📋 Phase 7: 飞书集成模块（计划中）

**状态**: 待规划  
**预计任务数**: 10-12 tasks

**目标**:
实现飞书机器人通知、多维表格同步、智能跟催

**计划功能**:
1. 飞书机器人消息推送
2. 卡片消息设计和发送
3. Webhook 事件接收
4. 多维表格数据同步
5. 智能问询跟催
6. 里程碑到期提醒
7. 任务逾期预警

---

### 📋 Phase 8: 定时任务系统（计划中）

**状态**: 待规划  
**预计任务数**: 6-8 tasks

**目标**:
实现 APScheduler 定时任务调度

**计划功能**:
1. 定时任务调度器配置
2. 逾期任务提醒
3. 进度问询跟催
4. 周报生成推送
5. 里程碑到期提醒
6. 飞书多维表格同步

---

### 📋 Phase 9: 报表和导入导出（计划中）

**状态**: 待规划  
**预计任务数**: 5-6 tasks

**目标**:
实现 Excel 导入导出和数据可视化

**计划功能**:
1. Excel 数据导入
2. Excel 报表导出
3. 看板统计数据
4. 项目进度报表
5. 周报/月报生成

---

### 📋 Phase 10: 前端开发（计划中）

**状态**: 待规划  
**预计任务数**: 15-20 tasks

**目标**:
实现 Vue 3 前端应用

**计划功能**:
1. 项目看板页面
2. 任务管理页面
3. 风险管理页面
4. 用户管理页面
5. 系统设置页面
6. 数据可视化图表

**技术栈**:
- Vue 3 + TypeScript
- Element Plus
- Pinia
- Vue Router
- Axios
- ECharts

---

### 📋 Phase 11: 部署和运维（计划中）

**状态**: 待规划  
**预计任务数**: 4-5 tasks

**目标**:
实现 Docker 容器化部署

**计划功能**:
1. Dockerfile 编写
2. Docker Compose 配置
3. 数据库备份脚本
4. 日志管理
5. 监控告警

---

## 技术栈总览

**后端**:
- FastAPI 0.110+
- SQLAlchemy 2.0+
- Alembic 1.13+
- Pydantic v2
- python-jose[cryptography]
- passlib[bcrypt]
- httpx
- APScheduler 3.10+
- openpyxl

**前端**:
- Vue 3 + TypeScript
- Element Plus
- Pinia
- Vue Router
- Axios
- ECharts

**数据库**:
- SQLite（开发）
- PostgreSQL（生产）

**部署**:
- Docker
- Docker Compose

---

## 开发进度

| Phase | 状态 | 进度 | 预计完成时间 |
|-------|------|------|------------|
| Phase 1: 项目初始化 | ✅ 已完成 | 100% | 2026-05-30 |
| Phase 2: 数据库模型 | ✅ 已完成 | 100% | 2026-05-30 |
| Phase 3: 认证系统 | ✅ 已完成 | 100% | 2026-05-30 |
| Phase 4: 项目管理 API | ✅ 已完成 | 100% | 2026-05-30 |
| Phase 5: 任务管理 API | ✅ 已完成 | 100% | 2026-05-30 |
| Phase 6: 风险管理 API | ✅ 已完成 | 100% | 2026-05-30 |
| Phase 7: 飞书集成 | 📋 计划中 | 0% | 2026-06-08 |
| Phase 8: 定时任务 | 📋 计划中 | 0% | 2026-06-10 |
| Phase 9: 报表导出 | 📋 计划中 | 0% | 2026-06-12 |
| Phase 10: 前端开发 | 📋 计划中 | 0% | 2026-06-20 |
| Phase 11: 部署运维 | 📋 计划中 | 0% | 2026-06-22 |

---

## 下一步行动

### 立即执行（Phase 3）

使用 Subagent-Driven Development 执行 Phase 3 认证系统：

```bash
# 在 Claude Code 中执行
/subagent-driven-development docs/superpowers/plans/2026-05-30-phase3-authentication-system.md
```

### 后续规划

1. 完成 Phase 3 后，立即规划 Phase 4（项目管理 API）
2. 每个 Phase 完成后进行代码审查和测试
3. 定期更新此路线图文档

---

## 参考文档

- **设计文档**: `docs/superpowers/specs/2026-05-30-feishu-project-manager-design.md`
- **Phase 2 计划**: `docs/superpowers/plans/2026-05-30-phase2-database-models.md`
- **Phase 3 计划**: `docs/superpowers/plans/2026-05-30-phase3-authentication-system.md`
- **Phase 3 代码补充**: `docs/superpowers/plans/2026-05-30-phase3-code-supplement.md`

---

**最后更新**: 2026-05-30  
**当前版本**: v0.6.0-dev
