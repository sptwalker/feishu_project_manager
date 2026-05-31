# 开发日志 2026-05-30

## 概述
本次更新完成了用户/项目解耦重构、Excel 导入增强、以及项目总览与详情页的全新实现。核心目标是支持非注册用户（Excel 导入、外部干系人）作为项目负责人/相关人，同时提供更直观的项目管理界面。

---

## 1. 用户/项目解耦重构

### 背景
原架构中 `projects.owner_id` 外键强制关联 `users` 表，导致 Excel 导入时必须为每个姓名创建用户记录，且无法支持外部干系人。

### 改动
- **数据库迁移** `a1b2c3d4e5f6_decouple_owner.py`
  - 删除 `projects.owner_id` / `tasks.owner_id` / `risks.owner_id` 外键
  - 新增 `owner_name` / `related_name` 文本字段（nullable）
  
- **模型层** (`models/project.py`, `task.py`, `risk.py`)
  - 移除 `owner_id` 关系，改用 `owner_name: str | None`
  - 新增 `related_name: str | None` 存储相关人（多个用逗号分隔）

- **Schema 层** (`schemas/project.py`, `task.py`, `risk.py`)
  - 创建/更新接口：接受 `owner_name` 替代 `owner_id`
  - 响应模型：返回 `owner_name` / `related_name`

- **Service 层** (`services/project_service.py`, `task_service.py`, `risk_service.py`)
  - 移除用户 FK 查找逻辑，直接存储姓名文本
  - 删除死代码 `UserService.get_or_create_by_name`（已无引用）

- **API 层** (`api/v1/projects.py`, `tasks.py`, `risks.py`, `reports.py`)
  - POST/PATCH 接口接受 `owner_name`
  - 报表接口适配文本字段过滤

- **测试覆盖**
  - 更新全部 204 个测试用例（fixtures、断言、权限检查）
  - 新增 `test_project_import.py` 验证 Excel 导入流程
  - 全部测试通过 ✅

### 影响
- ✅ 支持任意姓名作为负责人/相关人，无需预先注册
- ✅ 鉴权/权限系统不受影响（仍基于 `User.id` 和 `feishu_user_id`）
- ✅ 向后兼容：现有 API 调用方只需将 `owner_id` 改为 `owner_name`

---

## 2. Excel 导入增强

### 新增功能
- **负责人/相关人姓名导入**
  - 从 Excel 列直接提取 `owner_name` / `related_name`
  - 支持相关人多值（逗号分隔）

- **进展记录导入**
  - 新增 `progress_log` JSONB 列（迁移 `b2c3d4e5f6a7_add_related_and_progress.py`）
  - 从 Excel 解析进展记录列，存储为结构化数组：
    ```json
    [
      {"date": "2026-05-15", "content": "完成需求评审", "status": "正常"},
      {"date": "2026-05-20", "content": "等待设计稿", "status": "等待"}
    ]
    ```
  - 支持 8 种状态：正常/延迟/暂停/阻塞/等待/待讨论/待执行/待确认

### 实现细节
- **Excel 解析器** (`utils/excel.py`)
  - 新增 `_parse_progress_log()` 方法，支持多种分隔符（换行/分号）
  - 自动提取日期前缀（`YYYY-MM-DD:`）和状态标签（`【状态】`）

- **导入服务** (`services/import_service.py`)
  - 验证 progress_log 结构（日期格式、状态枚举）
  - 持久化到 `projects.progress_log` JSONB 字段

### 验证
- 使用 164 行真实数据测试，全部字段正确导入 ✅
- 进展记录时间线在详情页正确渲染 ✅

---

## 3. 项目总览与详情页

### 新增视图
#### **项目总览** (`ProjectOverviewView.vue`)
- 表格展示全部项目（部门/负责人/状态/优先级/完成度/日期）
- 双击行打开详情抽屉
- 支持按部门/状态/优先级筛选
- 逾期项目高亮显示

#### **项目详情抽屉** (`ProjectDetailDrawer.vue`)
- **可编辑字段**（点击铅笔图标进入编辑模式）：
  - 标题、简要说明
  - 完成情况（下拉选择）
  - 优先级（下拉选择）
  - 部门、负责人、相关人（支持输入/选择）
  - 记录日期、截止日期（日期选择器）
  - 完成度（滑块 0-100%）

- **进展记录时间线**（只读）：
  - 垂直时间线展示全部进展节点
  - 8 种状态对应不同颜色：
    - 正常 → 绿色
    - 延迟 → 橙色
    - 暂停 → 灰色
    - 阻塞 → 红色
    - 等待 → 蓝色
    - 待讨论 → 紫色
    - 待执行 → 青色
    - 待确认 → 黄色

- **保存逻辑**：
  - 点击「保存」调用 `PATCH /api/v1/projects/{id}`
  - 后端返回 204 → 前端更新本地状态 + 刷新表格
  - 验证通过：所有字段持久化正确 ✅

### 路由与导航
- 新增 `/projects` 路由，映射到 `ProjectOverviewView`
- 左侧导航栏「项目总览」高亮逻辑修正（`/projects` 和 `/board` 独立）

### API 集成
- 新增 `updateProject(id, data)` 方法（`api/resources.ts`）
- 类型定义：`ProgressLogEntry` / 扩展 `ProjectResponse`

---

## 4. 其他改进

### 清理与规范
- 删除死代码 `UserService.get_or_create_by_name`（解耦后无引用）
- 补充 `.gitignore`：忽略 `dev_seed.py` 和临时诊断脚本
- 统一 CRLF → LF（Git 自动转换警告已处理）

### 测试覆盖
- 全部 204 个后端测试通过 ✅
- 前端构建无错误 ✅
- 真实数据导入 + 详情页编辑流程验证通过 ✅

---

## 提交记录

```
a52df49 refactor: align user/auth/permissions with decoupled ownership
f1bff0e feat(frontend): add project overview with detail drawer
8be2068 feat(import): support owner/related names and progress logs in Excel
b759998 refactor: decouple user from project/task/risk ownership
4a4a1e8 chore: ignore dev scripts and remove dead code
```

---

## 下一步计划

1. **详情页增强**
   - 进展记录编辑功能（新增/修改/删除节点）
   - 附件上传与展示
   - 操作日志（谁在何时修改了哪些字段）

2. **权限细化**
   - 项目负责人可编辑自己的项目
   - 相关人只读权限
   - 管理员全局编辑权限

3. **飞书集成**
   - 项目状态变更推送飞书通知
   - 逾期提醒自动发送到负责人
   - 飞书日历同步截止日期

4. **性能优化**
   - 项目列表分页（当前全量加载）
   - 进展记录懒加载（超过 20 条折叠显示）

---

## 技术债务

- [ ] 前端类型定义需补充（部分 `any` 待替换为精确类型）
- [ ] 进展记录状态枚举需前后端统一（当前前端硬编码）
- [ ] Excel 导入错误处理需增强（当前遇到格式错误会整批失败）
- [ ] 详情抽屉的编辑状态在关闭时未清理（重新打开会保留上次编辑）

---

**开发者**: Walker + Claude Opus 4.8  
**日期**: 2026-05-30  
**版本**: v1.1.0-dev
