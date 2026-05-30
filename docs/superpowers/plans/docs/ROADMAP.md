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

### ✅ Phase 7: 飞书集成模块（已完成）

**状态**: 已完成  
**预计任务数**: 10-12 tasks

**目标**:
实现飞书机器人通知、多维表格同步、智能跟催

**计划功能**:
1. ✅ 飞书机器人消息推送（文本/卡片，tenant_access_token）
2. ✅ 卡片消息构建（任务/风险/项目通知卡片）
3. ✅ Webhook 事件接收（url_verification、token 校验、AES 解密、事件分发）
4. ✅ 多维表格(Bitable)数据同步（项目/任务 upsert）
5. ✅ 事件联动通知（任务/风险状态变更 → BackgroundTasks 推送负责人）

> 说明：智能问询跟催、里程碑到期提醒、任务逾期预警本质由定时任务驱动，
> 归入 Phase 8（定时任务系统）实现。

**安全设计**:
- 消息外发受配置开关 `FEISHU_NOTIFY_ENABLED` 控制，默认关闭；开发/测试期间不会真实外发
- 通知为尽力而为（best-effort），失败不影响主流程
- 全部测试 mock httpx/FeishuClient，无真实网络调用

**API 端点**:
- `POST /api/v1/feishu/webhook` - 接收飞书事件回调
- `POST /api/v1/bitable/projects/{project_id}/sync` - 同步项目到多维表格
- `POST /api/v1/bitable/tasks/{task_id}/sync` - 同步任务到多维表格

**相关文件**:
- `backend/core/feishu.py`（扩展：tenant token、send_text/send_card、bitable 记录操作）
- `backend/utils/feishu_cards.py`、`backend/utils/feishu_crypto.py`
- `backend/services/notification_service.py`、`backend/services/bitable_service.py`
- `backend/api/v1/feishu_webhook.py`、`backend/api/v1/bitable.py`
- `backend/tests/test_feishu_*.py`、`test_notification_service.py`、`test_bitable_service.py`
- 测试覆盖：37 个用例（client/crypto/cards/notification/webhook/bitable/wiring）

---

### ✅ Phase 8: 定时任务系统（已完成）

**状态**: 已完成
**实现方式**: APScheduler AsyncIOScheduler，集成于 FastAPI lifespan

**目标**:
实现 APScheduler 定时任务调度，驱动提醒/跟催/周报

**完成功能**:
1. ✅ 定时任务调度器配置（cron 触发，时区 TIMEZONE）
2. ✅ 逾期任务提醒（每天，due_date 已过且未完成）
3. ✅ 临期任务提醒（每天，N 天内到期）
4. ✅ 进度问询跟催（每天，进行中且 N 天未更新）
5. ✅ 里程碑到期提醒（每天，项目 estimated_end_date 已过）
6. ✅ 周报生成推送（每周，系统范围统计 → 配置接收人）

**安全设计**:
- 调度线程受 `SCHEDULER_ENABLED` 控制，默认关闭；测试/开发不自启后台线程
- 外发仍受 `FEISHU_NOTIFY_ENABLED` 控制（双层闸）
- 作业内部捕获异常并记录日志，单次失败不影响调度器存活
- 查询逻辑为纯函数，独立单测；编排部分 mock 通知

**未纳入（带理由）**:
- 飞书多维表格**定时**同步：当前模型未持久化 `feishu_record_id`，周期性同步会重复
  创建记录。需先加字段+迁移方可正确实现。Phase 7 已提供手动同步端点，此项延后。

**相关文件**:
- `backend/core/scheduler.py`（调度器配置、start/shutdown）
- `backend/services/reminder_service.py`、`backend/services/report_service.py`
- `backend/services/scheduler_jobs.py`
- `backend/core/config.py`（调度/提醒配置）、`backend/main.py`（lifespan）
- `backend/tests/test_reminder_service.py`、`test_reminder_jobs.py`、`test_scheduler.py`
- 测试覆盖：12 个用例（查询/编排/调度器闸/异常吞没）

---

### ✅ Phase 9: 报表和导入导出（已完成）

**状态**: 已完成
**实现方式**: openpyxl + 统计/导出/导入服务 + 报表 API

**目标**:
实现 Excel 导入导出和看板统计数据

**完成功能**:
1. ✅ Excel 任务导入（上传 xlsx，逐行校验，部分失败不影响其余）
2. ✅ Excel 报表导出（项目 / 项目任务，附件下载）
3. ✅ 看板统计数据（项目/任务/风险分布、逾期计数、平均完成度）
4. ✅ 项目进度报表（任务状态分布、完成率）
5. ✅ 周报生成（Phase 8 已实现 build_weekly_summary，统计服务复用同源数据）

**API 端点**:
- `GET /api/v1/statistics/dashboard` - 仪表盘统计
- `GET /api/v1/statistics/projects/{project_id}/progress` - 项目进度统计
- `GET /api/v1/reports/projects/export` - 导出全部项目为 Excel
- `GET /api/v1/reports/projects/{project_id}/tasks/export` - 导出项目任务为 Excel
- `POST /api/v1/reports/projects/{project_id}/tasks/import` - 从 Excel 导入任务

**相关文件**:
- `backend/utils/excel.py`（build_xlsx / parse_xlsx）
- `backend/services/statistics_service.py`、`export_service.py`、`import_service.py`
- `backend/schemas/statistics.py`、`backend/api/v1/reports.py`
- `backend/tests/test_excel_utils.py`、`test_reports_service.py`、`test_reports_api.py`
- 测试覆盖：23 个用例（excel/statistics/export/import/api）

---

### ✅ Phase 10: 前端开发（已完成）

**状态**: 已完成（核心 + 用户/设置全部页面）
**实现方式**: Vite + Vue 3 `<script setup>` + TS + Pinia + Vue Router + Element Plus + ECharts

**设计方向**: 「冷静的编辑式生产力」——暖灰白画布 + 墨黑文字 + 深靛蓝强调色 +
状态语义色，自定义设计 token 覆盖 Element Plus 默认观感。

**已完成功能**:
1. ✅ 应用骨架（左侧导航 + 顶栏 + 主区）
2. ✅ 登录页（飞书 OAuth 跳转）+ OAuth 回调页
3. ✅ 项目看板（统计卡片 + 卡片/列表视图切换 + 筛选 + 新建项目）
4. ✅ 任务管理（看板/表格视图切换 + 创建/编辑/删除 + 优先级/逾期标记）
5. ✅ API 层（Axios 封装：JWT 注入、401 自动刷新/跳登录）
6. ✅ 路由守卫（未登录拦截）+ Pinia auth store
7. ✅ 风险管理页（项目维度，按状态分列 + CRUD）
8. ✅ ECharts 可视化（项目状态环形图 + 任务状态柱状图）
9. ✅ 看板拖拽改状态（乐观更新，失败回滚）
10. ✅ 用户管理页（列表 + 角色修改，管理员）
11. ✅ 系统设置页（个人信息 + 系统概览）
12. ✅ 后端用户 API（/users/me、/users、PATCH 角色，含权限与 7 个测试）

**后端测试**: 184 passed（新增 7 个用户 API 用例）

**登录闭环**: ✅ 已打通——后端 `/auth/feishu/callback` 成功后 302 重定向到
`{FRONTEND_URL}/auth/callback?access_token=…&refresh_token=…`，前端读取并存入本地、
清理 URL；失败重定向到 `/login?error=…`。覆盖 5 个回调测试。

**构建验证**: `npm run build`（vue-tsc 2.x + vite）通过，exit 0。
> 注：原 `vue-tsc@1.8` 与 TS 5.9 不兼容，已升级到 2.x。

**技术栈**:
- Vue 3 + TypeScript
- Element Plus
- Pinia
- Vue Router
- Axios
- ECharts（项目状态环形图 + 任务状态柱状图，已接入）

---

### ✅ Phase 11: 部署和运维（已完成）

**状态**: 已完成（配置就绪并通过静态校验）

**目标**:
实现 Docker 容器化部署

**完成内容**:
1. ✅ 后端 Dockerfile（修正包布局：代码置于 `/app/backend`，`PYTHONPATH=/app`，
   `uvicorn backend.main:app`，解决绝对导入问题）
2. ✅ 容器入口脚本 `docker-entrypoint.sh`（启动前自动执行 `alembic upgrade head`）
3. ✅ alembic 纳入 requirements；`env.py` 改为从应用配置读取 `DATABASE_URL`
   （迁移与应用使用同一数据库，消除路径分叉）
4. ✅ 前端 Dockerfile 改用 `npm ci`（基于 lockfile，可复现构建）+ nginx 反代 `/api`
5. ✅ `docker-compose.yml`（生产）+ `docker-compose.dev.yml`（热重载）
   — 数据卷挂载至 `/data`，`DATABASE_URL=sqlite:////data/feishu_pm.db`
6. ✅ `docker/.env.example` 重写，键名与 `config.py` 完全对齐（修正原 `JWT_*` 错名、
   去除会导致 pydantic 解析失败的 `CORS_ORIGINS`、补齐安全闸默认值）
7. ✅ `.gitattributes` 强制 `*.sh` 用 LF（避免容器内脚本因 CRLF 失败）

**验证**:
- `docker compose config`（prod + dev）均通过
- 容器导入目标 `backend.main:app` 在等价布局下本地验证可导入（FastAPI 实例）
- `alembic upgrade head` 本地通过；后端测试 184 passed

**未完成（环境限制）**:
- 未能在本机实际 `docker build` 镜像并运行容器：本机 Docker Desktop 守护进程未启动
  （`docker --version` 可用，但 daemon 未运行）。配置已通过静态校验，构建需在
  daemon 可用的环境执行 `cd docker && cp .env.example .env && docker compose up -d`。

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
| Phase 7: 飞书集成 | ✅ 已完成 | 100% | 2026-05-30 |
| Phase 8: 定时任务 | ✅ 已完成 | 100% | 2026-05-30 |
| Phase 9: 报表导出 | ✅ 已完成 | 100% | 2026-05-30 |
| Phase 10: 前端开发 | ✅ 已完成 | 100% | 2026-05-30 |
| Phase 11: 部署运维 | ✅ 已完成 | 100% | 2026-05-30 |

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
**当前版本**: v1.0.0
