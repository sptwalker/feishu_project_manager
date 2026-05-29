# 飞书联动项目管理系统设计文档

**项目名称**: feishu_project_manager  
**设计日期**: 2026-05-30  
**版本**: v1.0

## 1. 项目概述

### 1.1 项目定位
一款面向小团队（10-50人）的轻量化中长期项目进度管理系统，深度集成飞书生态，聚焦核心功能而非复杂的甘特图和资源调度。

### 1.2 目标用户
- 项目经理：跟踪多个项目进度，管理里程碑和风险
- 团队成员：更新任务状态，查看相关项目信息
- 高层管理者：查看整体项目概览和数据统计

### 1.3 核心价值
- **轻量化**: 简化UI，快速部署，无需复杂培训即可上手
- **中长期**: 面向3-12个月的项目，按季度/月度管理
- **飞书深度集成**: OAuth登录、机器人通知、智能跟催、多维表格同步
- **完整溯源**: 事件时间线记录所有历史变更

## 2. 功能优先级

**P0 核心功能**:
1. 项目里程碑跟踪（关键节点、交付物）
2. 任务分配与状态更新（谁在做什么、完成度）
3. 风险与问题管理（阻塞项、延期预警）

**P1 重要功能**:
4. 飞书机器人通知与智能跟催
5. 事件时间线与历史追溯
6. Excel导入导出与定期报表

**P2 增强功能**:
7. 会议记录管理
8. 文档关联
9. 数据可视化看板

## 3. 系统架构设计

### 3.1 技术栈选型

**后端技术栈**:
- FastAPI 0.110+: 异步API框架，性能优异
- SQLAlchemy 2.0+: ORM + Alembic数据库迁移
- Pydantic v2: 数据校验和序列化
- APScheduler 3.10+: 定时任务调度
- python-jose: JWT token生成
- openpyxl: Excel读写
- httpx: 飞书API调用（异步HTTP客户端）
- lark-oapi: 飞书开放平台SDK

**前端技术栈**:
- Vue 3 + TypeScript
- Element Plus: UI组件库
- Pinia: 状态管理
- Vue Router: 路由管理
- Axios: HTTP客户端
- ECharts: 数据可视化

**数据库**:
- SQLite: 小团队零配置部署，后续可平滑迁移到PostgreSQL

### 3.2 架构分层

**三层架构**:
- **表现层**: Vue3前端 + FastAPI路由层
- **业务层**: Services处理业务逻辑 + Schemas数据校验
- **数据层**: SQLAlchemy ORM + SQLite数据库

**核心模块**:
1. 认证模块: 飞书OAuth登录、JWT token管理
2. 项目管理模块: 项目CRUD、里程碑跟踪、状态流转
3. 任务管理模块: 任务分配、进度更新、依赖关系
4. 风险管理模块: 风险登记、问题跟踪、预警机制
5. 飞书集成模块: 消息推送、日报生成、多维表格同步、智能跟催
6. 报表模块: Excel导入导出、定时报表生成
7. 定时任务模块: APScheduler调度器、任务配置
8. 事件溯源模块: 记录所有历史变更

### 3.3 数据流向

**用户操作流**:
```
用户操作 → Vue前端 → FastAPI接口 → Service业务逻辑 → SQLAlchemy → SQLite
```

**定时任务流**:
```
APScheduler → Service → 飞书API/Excel生成 → 数据库更新
```

**飞书回调流**:
```
飞书Webhook → FastAPI接口 → Service → 数据库更新 → 事件记录
```

## 4. 数据模型设计

### 4.1 核心实体

**项目表 (Project)**:
- id: 主键
- name: 事项名称
- record_date: 记录日期
- content: 内容描述
- status: 当前状态 (planned/in_progress/completed/cancelled)
- urgency: 紧急程度 (low/medium/high/urgent)
- department: 负责部门
- owner_id: 负责人ID (外键 → User)
- completion: 完成度 (0-100)
- estimated_end_date: 预计完成时间
- actual_end_date: 实际完成时间
- created_at, updated_at: 时间戳

**任务表 (Task)**:
- id: 主键
- project_id: 所属项目 (外键 → Project)
- parent_task_id: 父任务ID (自关联，支持子任务)
- name: 任务名称
- description: 描述
- owner_id: 负责人ID (外键 → User)
- status: 当前状态 (pending/in_progress/completed/blocked)
- priority: 优先级 (low/medium/high)
- completion: 完成度 (0-100)
- due_date: 截止日期
- start_date: 开始时间
- end_date: 完成时间
- created_at, updated_at: 时间戳

**事件表 (Event)** - 核心溯源表:
- id: 主键
- event_type: 事件类型 (status_change/assignee_change/progress_update/date_adjust/risk_event/association/system_event)
- entity_type: 关联对象类型 (project/task/meeting)
- entity_id: 关联对象ID
- triggered_by: 触发人ID (外键 → User)
- occurred_at: 发生时间
- change_details: 变更详情 (JSON字段，存储变更前后的值)
- description: 事件描述
- related_meeting_ids: 关联会议ID列表 (JSON)
- related_document_ids: 关联文档ID列表 (JSON)

**进度记录表 (ProgressLog)**:
- id: 主键
- entity_type: 关联对象类型 (project/task)
- entity_id: 关联对象ID
- updated_by: 更新人ID (外键 → User)
- updated_at: 更新时间
- content: 进度描述
- completion_change: 完成度变化 (JSON: {from: 50, to: 70})
- attachments: 附件列表 (JSON: [{name, url}])

**会议记录表 (MeetingNote)**:
- id: 主键
- title: 会议主题
- meeting_time: 会议时间
- participants: 参会人ID列表 (JSON)
- content: 会议纪要 (富文本)
- action_items: 待办事项列表 (JSON)
- created_by: 创建人ID
- created_at, updated_at: 时间戳

**文档表 (Document)**:
- id: 主键
- name: 文件名
- file_url: 文件URL/路径
- file_type: 文件类型 (feishu_doc/local_file/external_link)
- entity_type: 关联对象类型 (project/task/meeting)
- entity_id: 关联对象ID
- uploaded_by: 上传人ID
- uploaded_at: 上传时间

**风险表 (Risk)**:
- id: 主键
- project_id: 所属项目 (外键 → Project)
- title: 风险标题
- description: 风险描述
- impact: 影响程度 (low/medium/high)
- probability: 发生概率 (low/medium/high)
- mitigation: 应对措施
- status: 状态 (open/monitoring/resolved)
- owner_id: 责任人ID
- created_at, updated_at: 时间戳

**用户表 (User)**:
- id: 主键
- feishu_user_id: 飞书用户ID (唯一)
- name: 姓名
- avatar_url: 头像URL
- department: 部门
- role: 角色 (admin/project_manager/member/observer)
- last_login_at: 最后登录时间
- created_at: 创建时间

**关联表**:
- project_participants: 项目相关人 (多对多: Project ↔ User)
- task_collaborators: 任务协作人 (多对多: Task ↔ User)
- task_dependencies: 任务依赖关系 (Task ↔ Task)
- meeting_projects: 会议关联项目 (多对多: Meeting ↔ Project)
- meeting_tasks: 会议关联任务 (多对多: Meeting ↔ Task)

### 4.2 数据库索引策略

**关键索引**:
- project.status, project.owner_id, project.department
- task.project_id, task.status, task.owner_id, task.due_date
- event.entity_type + entity_id (复合索引)
- event.occurred_at (时间线查询)
- user.feishu_user_id (唯一索引)

## 5. 飞书集成设计

### 5.1 OAuth登录流程

1. 用户点击"飞书登录"按钮
2. 重定向到飞书授权页面
3. 用户授权后回调到系统
4. 系统获取access_token和用户信息
5. 创建/更新用户记录，生成JWT token
6. 前端存储JWT token，后续请求携带

### 5.2 机器人消息推送

**消息类型**:
- **里程碑到期提醒**: 提前3天/1天/当天推送卡片消息
- **任务逾期预警**: 每日早上9点检测逾期任务，推送给负责人
- **风险升级通知**: 高优先级风险实时推送给项目经理
- **日报/周报**: 定时汇总项目进度并推送到群聊

**消息卡片设计**:
- 标题 + 状态标签
- 关键信息（负责人、截止日期、完成度）
- 交互按钮（已完成/进行中/遇到阻塞）
- 快速跳转链接

### 5.3 智能问询跟催

**触发机制**:
- 定时触发：每周五下午5点自动执行
- 手动触发：项目经理可在系统中手动发起

**跟催流程**:
1. 系统检查所有进行中的任务
2. 筛选本周应更新但未更新的任务
3. 向负责人发送卡片消息询问进度
4. 卡片包含快捷回复按钮：
   - "已完成" → 自动更新任务状态为completed
   - "进行中X%" → 弹出输入框填写完成度
   - "遇到阻塞" → 自动创建风险记录并通知项目经理
5. 48小时未回复自动升级提醒（抄送项目经理）

### 5.4 多维表格同步

**同步方向**:
- 飞书 → 系统：定时从多维表格导入项目数据（每小时/每天）
- 系统 → 飞书：项目状态变更时推送更新到多维表格

**字段映射**:
```
飞书多维表格字段 → 系统字段
事项名称 → project.name
记录日期 → project.record_date
内容 → project.content
当前状态 → project.status
紧急程度 → project.urgency
负责部门 → project.department
负责人 → project.owner_id
完成度 → project.completion
```

**冲突处理**:
- 以最后更新时间为准
- 系统记录同步日志，便于排查

### 5.5 Webhook接收

**接收事件**:
- 用户点击卡片按钮（任务状态更新）
- 用户回复机器人消息（进度更新）
- 多维表格数据变更（触发同步）

**安全验证**:
- 验证飞书Webhook签名
- 验证请求来源IP白名单

## 6. 前端页面设计

### 6.1 整体风格

- 设计语言：现代简约风格，参考飞书设计规范
- 主色调：飞书蓝（#3370FF）+ 中性灰色系
- 布局：左侧导航 + 顶部操作栏 + 主内容区

### 6.2 页面结构

**左侧导航菜单**:
- 项目看板（首页）
- 任务总览
- 会议记录
- 系统管理（仅管理员可见）

**顶部操作栏**:
- 全局搜索框
- 消息通知图标（飞书消息同步）
- 用户头像下拉菜单（个人设置、退出登录）

### 6.3 核心页面设计

**1. 项目看板页（Dashboard）**

**数据统计卡片区**（顶部4列）:
- 项目总数 / 进行中项目
- 本周到期任务数 / 逾期任务数
- 高风险项目数 / 本周完成任务数
- 团队工作量统计

**可视化图表区**:
- 项目状态分布（饼图）
- 部门项目数量对比（柱状图）
- 近30天完成趋势（折线图）
- 紧急程度分布（环形图）

**快速入口**:
- 待我处理
- 我负责的项目
- 最近更新

**2. 任务总览页**

**顶部操作栏**:
- 新建项目按钮
- 导入Excel按钮
- 导出报表按钮

**筛选器**（多条件组合）:
- 负责部门（多选下拉）
- 负责人（搜索选择）
- 紧急程度（低/中/高/紧急）
- 当前状态（计划中/进行中/已完成/已取消）
- 完成度范围（滑块选择0-100%）
- 时间范围（记录日期/截止日期）

**排序选项**:
- 记录日期
- 完成度
- 紧急程度
- 更新时间

**搜索框**:
- 支持项目名称、内容关键词搜索
- 实时搜索，输入即过滤

**表格视图**（可配置列）:
- 默认列：事项名称、负责部门、负责人、当前状态、完成度、紧急程度、记录日期
- 可选列：相关人、最新进度、逾期天数
- 行操作：点击行打开项目详情抽屉
- 支持多选批量操作

**分页器**:
- 支持每页显示数量调整（10/20/50/100）

**3. 项目详情抽屉（多层级）**

**第一层抽屉（项目详情，宽度60%）**:

*头部*:
- 项目名称 + 状态标签
- 操作按钮：编辑、导出、归档、关闭

*基本信息卡片*:
- 负责部门、负责人、相关人
- 记录日期、紧急程度
- 完成度进度条

*Tab切换*:
- **任务列表**：树形表格（父任务可展开显示子任务），点击任务行打开第二层抽屉
- **时间线**：垂直时间轴展示所有事件（状态变更、人员变更、文档上传、会议关联）
- **会议记录**：列表展示 + 快速添加按钮
- **文档中心**：文件列表 + 上传区域（支持飞书云文档链接）
- **风险管理**：风险/问题表格，支持添加、编辑、标记解决

*底部*:
- 最新进度记录（最近3条）
- 查看全部按钮

**第二层抽屉（任务详情，宽度50%）**:

*头部*:
- 任务名称 + 状态标签
- 关闭按钮

*任务信息*:
- 负责人、截止日期、优先级
- 完成度滑块（拖动即更新）

*描述区*:
- 富文本显示任务描述

*子任务列表*:
- 可展开，点击打开第三层抽屉
- 支持快速添加子任务

*进度更新区*:
- 富文本编辑器
- 附件上传（支持图片、文档）
- 提交按钮

*时间线*:
- 该任务的历史事件（创建、分配、状态变更、进度更新）

**第三层抽屉（子任务详情，宽度40%）**:
- 结构同第二层
- 支持继续嵌套子任务（最多3层）

**抽屉交互**:
- 面包屑导航显示当前层级
- 点击遮罩关闭当前层，保留下层抽屉
- Esc键逐层关闭抽屉

**4. 会议记录页**

**列表视图**:
- 会议主题、时间、参会人、关联项目数
- 支持筛选（时间范围、参会人）
- 支持搜索（会议主题、纪要内容）

**会议详情抽屉**:
- 会议基本信息
- 会议纪要（富文本显示）
- 待办事项列表（可一键转为任务）
- 关联项目/任务列表

**5. 系统管理设置页**

**页面布局**:
- 左侧Tab导航 + 右侧配置内容区

**Tab分类**:

**(1) 飞书集成配置**:
- 应用信息：App ID、App Secret（密文显示）、Verification Token
- OAuth配置：回调地址、权限范围
- 机器人配置：
  - 机器人名称、头像
  - 默认推送群聊ID
  - 消息模板编辑（提醒、跟催、日报格式）
- 多维表格同步：
  - 表格App Token、Table ID
  - 同步频率设置（每小时/每天）
  - 字段映射配置
- 连接测试按钮：测试飞书API连通性

**(2) 定时任务配置**:
- 任务列表（表格形式）：
  - 任务名称、执行时间（Cron表达式）、状态（启用/禁用）、最后执行时间
- 可配置任务：
  - 逾期任务提醒（默认每日9:00）
  - 进度问询跟催（默认每周五17:00）
  - 周报生成推送（默认每周一10:00）
  - 里程碑到期提醒（提前3天/1天）
- 操作：编辑时间、启用/禁用、立即执行（测试）
- 执行日志：查看最近10次执行记录

**(3) 用户与权限管理**:
- 用户列表：姓名、部门、角色、最后登录时间
- 角色配置：
  - 管理员（全部权限）
  - 项目经理（创建项目、分配任务、查看所有数据）
  - 团队成员（更新自己的任务、查看相关项目）
  - 观察者（只读权限）
- 部门管理：添加/编辑/删除部门

**(4) 系统参数配置**:
- 基础设置：
  - 系统名称、Logo上传
  - 时区设置
  - 语言选择（中文/英文）
- 业务规则：
  - 任务逾期定义（超过截止日期N天算逾期）
  - 风险等级阈值（完成度低于X%且距截止日期Y天内标记高风险）
  - 自动归档规则（完成后N天自动归档）
- 通知设置：
  - 邮件通知开关（如果支持）
  - 飞书通知开关（全局/按类型）
  - 免打扰时间段

**(5) 数据管理**:
- 数据备份：
  - 手动备份按钮（导出SQLite文件）
  - 自动备份配置（每周/每月）
  - 备份历史列表（下载/删除）
- 数据导入导出：
  - Excel模板下载
  - 批量导入项目/任务
  - 全量数据导出
- 数据清理：
  - 清理已归档项目（保留时间设置）
  - 清理历史日志（保留最近N天）

**(6) 系统日志**:
- 操作日志：用户操作记录（登录、创建、修改、删除）
- 接口日志：飞书API调用记录（成功/失败）
- 错误日志：系统异常记录
- 筛选：时间范围、日志类型、用户、关键词搜索

**权限控制**:
- 仅管理员角色可访问系统管理页面
- 非管理员访问时显示403无权限提示

### 6.4 UI组件增强

**空状态插画**:
- 无数据时显示友好提示和引导操作

**骨架屏加载**:
- 提升感知性能，避免白屏

**Toast通知**:
- 操作成功/失败反馈
- 自动消失（3秒）

**确认对话框**:
- 删除等危险操作二次确认

**响应式设计**:
- 支持平板/手机查看
- 移动端抽屉全屏显示

### 6.5 交互细节

**快捷键支持**:
- Ctrl+K：打开全局搜索
- Esc：逐层关闭抽屉
- Ctrl+S：保存当前编辑（如果适用）

**实时搜索**:
- 项目/任务/人员搜索
- 输入即过滤，无需点击搜索按钮

**批量操作**:
- 多选任务批量分配负责人
- 批量更新状态
- 批量导出

**拖拽排序**:
- 任务优先级调整
- 看板卡片拖拽改变状态

**表格列配置**:
- 用户可自定义显示列
- 保存用户偏好到本地存储

## 7. 后端API设计

### 7.1 RESTful API规范

**基础路径**: `/api/v1`

**认证方式**: JWT Bearer Token

**响应格式**:
```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

### 7.2 核心接口列表

**认证模块**:
- `GET /auth/feishu/login` - 飞书OAuth登录跳转
- `GET /auth/feishu/callback` - 飞书OAuth回调
- `POST /auth/refresh` - 刷新JWT token
- `POST /auth/logout` - 退出登录

**项目模块**:
- `GET /projects` - 获取项目列表（支持筛选、排序、分页）
- `POST /projects` - 创建项目
- `GET /projects/{id}` - 获取项目详情
- `PUT /projects/{id}` - 更新项目
- `DELETE /projects/{id}` - 删除项目
- `GET /projects/{id}/timeline` - 获取项目时间线
- `GET /projects/{id}/statistics` - 获取项目统计数据

**任务模块**:
- `GET /projects/{project_id}/tasks` - 获取项目任务列表
- `POST /projects/{project_id}/tasks` - 创建任务
- `GET /tasks/{id}` - 获取任务详情
- `PUT /tasks/{id}` - 更新任务
- `DELETE /tasks/{id}` - 删除任务
- `POST /tasks/{id}/subtasks` - 创建子任务
- `GET /tasks/{id}/timeline` - 获取任务时间线

**进度记录模块**:
- `POST /projects/{id}/progress` - 添加项目进度记录
- `POST /tasks/{id}/progress` - 添加任务进度记录
- `GET /progress/{id}` - 获取进度记录详情

**会议记录模块**:
- `GET /meetings` - 获取会议列表
- `POST /meetings` - 创建会议记录
- `GET /meetings/{id}` - 获取会议详情
- `PUT /meetings/{id}` - 更新会议记录
- `DELETE /meetings/{id}` - 删除会议记录

**文档模块**:
- `POST /documents` - 上传文档
- `GET /documents/{id}` - 获取文档详情
- `DELETE /documents/{id}` - 删除文档

**风险模块**:
- `GET /projects/{project_id}/risks` - 获取项目风险列表
- `POST /projects/{project_id}/risks` - 创建风险
- `PUT /risks/{id}` - 更新风险
- `DELETE /risks/{id}` - 删除风险

**飞书集成模块**:
- `POST /feishu/webhook` - 飞书事件回调接收
- `POST /feishu/sync/pull` - 从飞书多维表格拉取数据
- `POST /feishu/sync/push` - 推送数据到飞书多维表格
- `POST /feishu/notify/test` - 测试飞书通知

**报表模块**:
- `GET /reports/dashboard` - 获取看板统计数据
- `POST /reports/export` - 导出Excel报表
- `POST /reports/import` - 导入Excel数据

**系统管理模块**:
- `GET /admin/users` - 获取用户列表
- `PUT /admin/users/{id}/role` - 更新用户角色
- `GET /admin/settings` - 获取系统配置
- `PUT /admin/settings` - 更新系统配置
- `GET /admin/logs` - 获取系统日志
- `POST /admin/backup` - 手动备份数据

## 8. 定时任务设计

### 8.1 任务调度器

使用APScheduler实现定时任务调度。

**任务配置存储**:
- 存储在数据库中（ScheduledTask表）
- 支持动态启用/禁用
- 支持Cron表达式配置

### 8.2 预定义任务

**1. 逾期任务提醒**:
- 执行时间：每日早上9:00
- 逻辑：
  1. 查询所有状态为in_progress且due_date < 今天的任务
  2. 向每个任务的负责人发送飞书卡片消息
  3. 记录提醒事件到Event表

**2. 进度问询跟催**:
- 执行时间：每周五下午5:00
- 逻辑：
  1. 查询所有进行中的任务
  2. 筛选本周未更新进度的任务
  3. 向负责人发送交互式卡片消息
  4. 记录跟催事件

**3. 周报生成推送**:
- 执行时间：每周一早上10:00
- 逻辑：
  1. 汇总上周完成的任务、新增的项目、高风险项
  2. 生成周报内容
  3. 推送到配置的飞书群聊
  4. 可选：生成Excel附件

**4. 里程碑到期提醒**:
- 执行时间：每日早上8:00
- 逻辑：
  1. 查询距离截止日期3天/1天/当天的里程碑
  2. 向项目负责人和相关人发送提醒
  3. 记录提醒事件

**5. 飞书多维表格同步**:
- 执行时间：每小时（可配置）
- 逻辑：
  1. 从飞书多维表格拉取数据
  2. 对比本地数据，识别新增/更新/删除
  3. 同步到本地数据库
  4. 记录同步日志

### 8.3 任务失败处理

- 最多重试3次
- 记录失败日志到系统日志
- 发送告警通知给管理员（如果连续失败）

## 9. 部署与运维

### 9.1 部署方案

**Docker Compose一键部署**:

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    env_file:
      - .env
  
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - frontend
      - backend
```

**环境变量配置（.env）**:
```
# 飞书配置
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_VERIFICATION_TOKEN=xxx
FEISHU_ENCRYPT_KEY=xxx

# JWT配置
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# 数据库配置
DATABASE_URL=sqlite:///./data/feishu_pm.db

# 系统配置
TIMEZONE=Asia/Shanghai
LOG_LEVEL=INFO
```

### 9.2 数据持久化

- SQLite文件挂载到宿主机 `./data` 目录
- 上传的文档存储在 `./data/uploads` 目录
- 日志文件存储在 `./data/logs` 目录

### 9.3 反向代理配置

Nginx配置：
- 静态文件直接服务
- `/api` 路径转发到后端
- WebSocket支持（如果需要实时通知）

## 10. 安全设计

### 10.1 认证与授权

**JWT Token机制**:
- Access Token有效期：7天
- Token存储在前端localStorage
- 每次请求携带Bearer Token
- Token过期自动跳转登录页

**权限控制**:
- 基于角色的访问控制（RBAC）
- 四种角色：管理员、项目经理、团队成员、观察者
- 接口级权限校验
- 前端路由守卫

### 10.2 数据安全

**SQL注入防护**:
- 使用SQLAlchemy参数化查询
- 禁止拼接SQL语句

**XSS防护**:
- 前端输入过滤
- 后端输出转义
- Content-Security-Policy头

**CSRF防护**:
- JWT Token验证
- SameSite Cookie属性

**敏感信息保护**:
- 飞书App Secret加密存储
- 日志中脱敏处理
- 数据库备份加密

### 10.3 飞书集成安全

**Webhook签名验证**:
- 验证飞书请求签名
- 防止伪造请求

**API调用限流**:
- 飞书API调用频率控制
- 避免触发限流

**CORS配置**:
- 仅允许前端域名跨域访问
- 生产环境严格配置

## 11. 测试策略

### 11.1 单元测试

**测试框架**: pytest

**测试覆盖**:
- Service层业务逻辑（目标覆盖率80%）
- 工具类函数（Excel处理、日期计算）
- 数据模型验证

### 11.2 集成测试

**测试场景**:
- 飞书OAuth登录流程
- 飞书API调用（使用Mock）
- Excel导入导出功能
- 定时任务执行

**测试工具**:
- pytest-asyncio（异步测试）
- httpx MockTransport（HTTP Mock）

### 11.3 端到端测试（可选）

**测试框架**: Playwright

**关键用户流程**:
- 登录 → 创建项目 → 添加任务 → 更新进度
- 查看时间线 → 添加会议记录 → 导出报表

### 11.4 手动测试重点

- 飞书机器人交互（卡片按钮点击、回复处理）
- 定时任务触发验证
- 多层级抽屉交互
- 移动端响应式布局

## 12. 错误处理

### 12.1 全局异常捕获

**后端**:
- FastAPI全局异常处理器
- 统一错误响应格式
- 错误码定义（业务错误、系统错误）

**前端**:
- Axios拦截器统一处理
- 友好错误提示
- 网络错误重试机制

### 12.2 飞书API失败处理

- 自动重试机制（最多3次，指数退避）
- 失败日志记录
- 降级策略（API失败不影响核心功能）

### 12.3 定时任务失败处理

- 记录失败日志
- 发送告警通知给管理员
- 支持手动重新执行

## 13. 项目目录结构

```
feishu_project_manager/
├── backend/                      # 后端根目录
│   ├── api/                      # 接口路由层
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── auth.py           # 认证路由
│   │   │   ├── projects.py       # 项目路由
│   │   │   ├── tasks.py          # 任务路由
│   │   │   ├── meetings.py       # 会议路由
│   │   │   ├── feishu.py         # 飞书集成路由
│   │   │   ├── reports.py        # 报表路由
│   │   │   └── admin.py          # 系统管理路由
│   ├── core/                     # 核心配置
│   │   ├── config.py             # 配置管理
│   │   ├── security.py           # JWT、权限校验
│   │   ├── scheduler.py          # 定时任务调度器
│   │   └── dependencies.py       # FastAPI依赖注入
│   ├── db/                       # 数据库
│   │   ├── database.py           # 数据库连接
│   │   ├── base.py               # Base模型
│   │   └── migrations/           # Alembic迁移文件
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── task.py
│   │   ├── event.py
│   │   ├── meeting.py
│   │   ├── document.py
│   │   ├── risk.py
│   │   └── enums.py              # 枚举类型
│   ├── schemas/                  # 数据校验、入参出参
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── task.py
│   │   ├── event.py
│   │   └── common.py             # 通用Schema
│   ├── services/                 # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── project_service.py
│   │   ├── task_service.py
│   │   ├── event_service.py
│   │   ├── feishu_service.py     # 飞书集成服务
│   │   ├── report_service.py     # 报表服务
│   │   └── scheduler_service.py  # 定时任务服务
│   ├── utils/                    # 工具类
│   │   ├── excel_helper.py       # Excel处理
│   │   ├── logger.py             # 日志工具
│   │   ├── date_helper.py        # 日期工具
│   │   └── crypto.py             # 加密工具
│   ├── tests/                    # 测试目录
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── main.py                   # 项目入口
│   ├── requirements.txt          # 依赖清单
│   └── Dockerfile
├── frontend/                     # 前端Vue项目
│   ├── src/
│   │   ├── api/                  # API调用封装
│   │   ├── assets/               # 静态资源
│   │   ├── components/           # 公共组件
│   │   ├── layouts/              # 布局组件
│   │   ├── router/               # 路由配置
│   │   ├── stores/               # Pinia状态管理
│   │   ├── utils/                # 工具函数
│   │   ├── views/                # 页面组件
│   │   │   ├── Dashboard.vue
│   │   │   ├── ProjectList.vue
│   │   │   ├── MeetingList.vue
│   │   │   └── Admin/
│   │   ├── App.vue
│   │   └── main.ts
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker/                       # 部署配置
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── .env.example
├── docs/                         # 项目文档
│   ├── superpowers/
│   │   └── specs/
│   │       └── 2026-05-30-feishu-project-manager-design.md
│   ├── api/                      # API文档
│   └── deployment.md             # 部署文档
└── README.md                     # 项目说明

```

## 14. 初始化流程

### 14.1 飞书应用配置

1. 登录飞书开放平台（https://open.feishu.cn）
2. 创建企业自建应用
3. 配置应用权限：
   - 获取用户信息
   - 发送消息
   - 访问多维表格
4. 配置OAuth回调地址：`https://your-domain.com/api/v1/auth/feishu/callback`
5. 配置事件订阅（Webhook）：`https://your-domain.com/api/v1/feishu/webhook`
6. 获取App ID、App Secret、Verification Token

### 14.2 系统部署步骤

1. 克隆GitHub仓库：
   ```bash
   git clone https://github.com/sptwalker/feishu_project_manager.git
   cd feishu_project_manager
   ```

2. 配置环境变量：
   ```bash
   cp docker/.env.example docker/.env
   # 编辑.env文件，填写飞书配置
   ```

3. 启动服务：
   ```bash
   cd docker
   docker-compose up -d
   ```

4. 初始化数据库：
   ```bash
   docker exec -it backend alembic upgrade head
   ```

5. 访问系统：
   - 前端：http://localhost
   - 后端API文档：http://localhost/api/docs

6. 首次登录：
   - 点击"飞书登录"按钮
   - 授权后自动创建管理员账号

### 14.3 初始配置

1. 登录系统后进入"系统管理"
2. 配置飞书集成参数
3. 配置定时任务执行时间
4. 添加部门和用户
5. 测试飞书通知功能

## 15. 开发规范

### 15.1 代码规范

**后端**:
- 遵循PEP 8规范
- 使用Black格式化代码
- 使用Pylint静态检查
- 类型注解（Type Hints）

**前端**:
- 遵循Vue 3官方风格指南
- 使用ESLint + Prettier
- TypeScript严格模式
- 组件命名：PascalCase

### 15.2 Git提交规范

使用Conventional Commits规范：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

示例：`feat(project): add timeline view`

### 15.3 分支管理

- `main`: 生产环境分支
- `develop`: 开发分支
- `feature/*`: 功能分支
- `bugfix/*`: 修复分支

## 16. 后续扩展方向

### 16.1 短期优化（1-3个月）

- 移动端App（React Native/Flutter）
- 实时通知（WebSocket）
- 数据可视化增强（更多图表类型）
- AI辅助任务拆分（集成LLM）

### 16.2 中期扩展（3-6个月）

- 多租户支持（SaaS化）
- 更多第三方集成（钉钉、企业微信）
- 高级报表（自定义报表模板）
- 项目模板库

### 16.3 长期规划（6-12个月）

- 迁移到PostgreSQL（支持更大规模）
- 微服务架构拆分
- 国际化支持
- 开放API平台

## 17. 风险与挑战

### 17.1 技术风险

- **SQLite并发限制**: 小团队够用，但需监控写入冲突
- **飞书API限流**: 需要合理控制调用频率
- **定时任务可靠性**: 单机部署可能存在单点故障

### 17.2 业务风险

- **用户习惯培养**: 需要引导用户及时更新进度
- **数据质量**: 依赖用户输入的准确性
- **权限管理**: 需要明确各角色职责边界

### 17.3 应对措施

- 监控SQLite性能，必要时迁移PostgreSQL
- 实现飞书API调用队列和限流
- 定时任务失败告警机制
- 用户培训和操作指南
- 数据校验和提示优化

## 18. 总结

本设计文档定义了飞书联动项目管理系统的完整架构和实现方案。系统采用FastAPI + Vue3 + SQLite技术栈，聚焦轻量化和核心功能，深度集成飞书生态，提供项目里程碑跟踪、任务管理、智能跟催、事件溯源等功能。

**核心特点**:
- 轻量化部署，适合小团队快速上手
- 飞书深度集成，提升协作效率
- 完整事件溯源，历史可追溯
- 多层级抽屉设计，信息层次清晰

**下一步**:
- 编写详细的实现计划
- 搭建项目基础框架
- 实现核心功能模块
- 集成飞书API
- 测试与部署

