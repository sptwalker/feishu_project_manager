# 用户自助注册 + 管理员用户管理 — 设计文档

- 日期：2026-05-31
- 状态：已确认，进入实现

## 背景与现状

- 飞书 OAuth 登录**已实现自助注册**：用户飞书登录后若系统无账户，`auth_service.feishu_login` 会自动创建用户（默认角色 `member`）。
- `User` 模型现有字段：`feishu_user_id`、`name`(中文名)、`avatar_url`、`department`、`role`、`last_login_at`。
- 用户 API 现有：`GET /users/me`、`GET /users`、`PATCH /users/{id}/role`。
- 前端 `UserManagement.vue` 已有"新增用户"按钮和"修改角色"对话框；`resources.ts` 声明了 `userApi.create/update/remove`，但后端**未实现** create/update/remove。
- 飞书 `/authen/v1/user_info` 返回包含 `name`、`en_name`、`avatar_url` 等，英文名可自动带入。

## 决策（来自需求澄清）

1. 新用户首次飞书登录后初始状态 = **`member`**，不引入审批机制。
2. 管理模型 = **纯管理模式**：移除手动"新增用户"，所有人通过飞书登录自助注册，管理员只编辑已注册用户。
3. 职位字段 = **自由文本**。
4. 编辑界面 = **方案 A 统一"编辑用户"对话框**（一处编辑角色/职位/中英文名/部门）。
5. 部门字段存**全称**（与现有数据与项目总览匹配逻辑一致），显示带颜色。
6. 本次**不做**删除用户功能。

## ① 数据模型变更

`User` 表新增两列（均可空）：
- `name_en` `String(100)` — 英文姓名
- `position` `String(100)` — 职位

字段语义：

| 字段 | 含义 | 来源 |
|---|---|---|
| `name` | 中文姓名（已有） | 飞书 `name` |
| `name_en` | 英文姓名（新） | 飞书 `en_name`，管理员可改 |
| `position` | 职位（新） | 注册时空，管理员填 |
| `department` | 所属部门（已有） | 飞书 `department_name`，管理员可改为部门表中的部门 |
| `role` | 权限角色（已有） | 默认 `member`，管理员可改 |

Alembic 迁移：向 `users` 表 `add_column` 这两列。

## ② 飞书自助注册流程（增强）

`auth_service.feishu_login` 创建用户时增加 `name_en ← user_info["en_name"]`，其余不变。`UserCreate` schema 增加可选 `name_en`。`UserService.create` 写入 `name_en`。

## ③ 后端 API

- 新增 `PUT /users/{id}`（仅管理员 `get_current_admin`）：可编辑 `role`、`position`、`name`、`name_en`、`department`。
- 新增 `UserUpdate` schema（全部字段可选）。
- `UserResponse` 增加 `name_en`、`position`。
- `UserService.update(db, user_id, data)` 方法。
- 保留 `PATCH /users/{id}/role`（向后兼容，前端不再单独调用）。
- 不实现 `POST /users` 与删除用户。

## ④ 前端界面

`UserManagement.vue`：
- 移除"新增用户"按钮。
- "修改角色"对话框升级为"编辑用户"对话框，字段：角色（下拉）、职位（文本）、中文名（文本）、英文名（文本）、所属部门（下拉，选项来自部门表，带颜色）。
- 表格新增列：英文名、职位；部门列沿用部门表颜色。

`types.ts`：`User` 接口加 `name_en`、`position`。
`resources.ts`：`userApi.update` 对接 `PUT /users/{id}`；移除未实现的 `create` 使用。

## ⑤ 权限与错误处理

- 编辑端点仅管理员，非管理员 → `403`。
- 编辑不存在用户 → `404`。
- 部门可留空。

## ⑥ 测试

- 后端：`UserService.update` 单元测试；`PUT /users/{id}` 权限测试（管理员 200 / 非管理员 403 / 不存在 404）；飞书注册带入 `en_name` 测试。
- 前端：手动验证编辑流程与字段保存。
