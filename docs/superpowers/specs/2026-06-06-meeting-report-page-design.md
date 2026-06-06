# 周例会汇报页（Meeting Report Page）设计规格

- **日期**：2026-06-06
- **作者**：Walker + Claude（brainstorming 流程产出）
- **状态**：待用户复审
- **布局定稿**：方案 A1（三栏 · 部门-个人树 + 梯形主席台顶栏 + 详情最大化）

---

## 1. 背景与目标

每周例会上需要按"部门 → 负责人"的顺序，逐一汇报所有**待启动 / 进行中 / 暂停**的项目。当前系统（项目总览、详情抽屉）面向日常管理，不适合会议大屏：信息分散、无汇报节奏、无计时约束。

本功能新增一个**全屏汇报页**，目标：

1. 全屏展示，按"部门 → 个人"顺序组织，逐一汇报。
2. 一屏看全负责人列表 + 当前项目进展详情，可实时编辑。
3. 方便翻页（上一位/下一位）与查找项目。
4. 醒目的双计时：总会议倒计时 + 当前汇报人计时；单人超阈值时醒目提示。
5. 记录会议起止时间与主要信息到后端（少量持久化）。

**成功标准**：主持人能在一个页面内完成"按部门-个人顺序逐项目汇报、实时改进展、控时"全流程，无需切换到其他页面。

---

## 2. 现状分析（带代码出处）

| 关注点 | 现状 | 出处 |
|--------|------|------|
| 项目状态枚举 | `planned/in_progress/paused/completed/cancelled`，"待启动/进行中/暂停"对应前三者 | [backend/models/project.py:6](../../../backend/models/project.py) / [frontend/src/types.ts:3](../../../frontend/src/types.ts) |
| 负责人 / 部门 | `owner_name`、`department` 均为字符串字段（与账号解耦） | [backend/models/project.py:30-32](../../../backend/models/project.py) |
| 进展记录 | `progress_log: ProgressEntry[]`（time/content/status/批注/附件） | [frontend/src/types.ts:55](../../../frontend/src/types.ts) |
| 实时编辑保存 | 复用 `projectApi.update(id, {progress_log})` → `PUT /projects/{id}` | [frontend/src/api/resources.ts:14](../../../frontend/src/api/resources.ts)、[ProjectDetailDrawer.vue:990](../../../frontend/src/components/ProjectDetailDrawer.vue) |
| 项目详情 UI | 重量级抽屉组件（含进展/批注/附件/历史） | [frontend/src/components/ProjectDetailDrawer.vue](../../../frontend/src/components/ProjectDetailDrawer.vue) |
| 全文搜索 | 已有 `projectSearchBlob` / `findDepartment`（容错全称/简称） | [ProjectOverviewView.vue:212-262](../../../frontend/src/views/ProjectOverviewView.vue) |
| 原生拖拽 | 已有 HTML5 draggable 拖拽改状态模式（无第三方库） | [TaskBoardView.vue:216-244](../../../frontend/src/views/TaskBoardView.vue) |
| 周会开关/归档 | `open_meeting`/`close_meeting`，以 `meeting_records` 表为真相源 | [meeting_record_service.py:157-200](../../../backend/services/meeting_record_service.py) |
| 通用键值存储 | `SettingsService.get_setting/set_setting`（存字符串） | [settings_service.py:44-63](../../../backend/services/settings_service.py) |
| 操作日志 | `OperationLogService.log()`（独立吞异常，不影响主流程） | [operation_log_service.py:21-56](../../../backend/services/operation_log_service.py) |
| 周会前端状态 | `useMeetingStore`（次数/active） | [frontend/src/stores/meeting.ts:6](../../../frontend/src/stores/meeting.ts) |
| 路由 | 顶层 public/非 public 路由；业务页挂在 AppLayout children 下 | [frontend/src/router/index.ts:6-41](../../../frontend/src/router/index.ts) |

---

## 3. 范围

### 3.1 在范围内
- 全屏汇报页（路由 `/meeting-report`，独立于 AppLayout，无侧边栏）。
- 左侧"部门 ▸ 个人 ▸ 项目"两级拖拽树 + 查找。
- 顶部梯形主席台：会议信息、总时长倒计时、汇报人（带翻页箭头）、本人计时、查看纪要/设置入口。
- 右侧项目进展详情：页头固定、进展区滚动、全字段可编辑。
- 汇报顺序持久化（后端 SystemSetting），下次默认沿用。
- 双计时（前端运行时）+ 单人统一阈值超时提示。
- 后端记录会议起止时间（MeetingRecord 加列）与主要信息日志。

### 3.2 明确不做（YAGNI）
- 不做多人实时协同/WebSocket 同步（编辑仍走现有 REST，乐观刷新）。
- 不做计时数据入库/历史计时报表（计时纯运行时，刷新即重置）。
- 不做单人独立预算（仅一个统一阈值）。
- 不改动飞书纪要生成逻辑（"查看会议纪要"复用现有 `send` 流程）。
- 不展示 completed/cancelled 项目。

---

## 4. 用户交互与布局（A1 定稿）

```
┌─────────────────────────────────────────────────────────────┐
│ 周例会·第N次  总28:30        ╔══════════════╗   [查看纪要][⚙] │
│ 2026-06-05                   ║ ‹ 研发部·张三 › ║               │  ← 梯形主席台
│                              ╚═ 本人 04:12 ═╝   （上大下小，下嵌）│
├──────────────┬──────────────────────────────────────────────┤
│ 🔍查找 ⇅排序  │ 📌页头固定：项目名 状态 紧急度 负责人 完成度    │
│ ▸研发部       │──────────────────────────────────────────────│
│   ▾张三(3)    │ 进展详情（可滚动·可编辑）                       │
│     •项目甲   │   05-20 ……                                    │
│     •项目乙   │   05-13 ……                                    │
│   李四(2)     │   05-06 ……                                    │
│ ▸市场部       │                                               │
│ ▸未分配       │                                               │
└──────────────┴──────────────────────────────────────────────┘
```

**顶栏梯形主席台**：上宽下窄，下沿嵌入内容区约 30px。
- 左侧：会议信息（周例会·第N次 + 日期）与 **总时长倒计时** 同排。
- 中部梯形：上行 = 汇报人「‹ 部门·姓名 ›」（箭头贴姓名两侧，点击切换上一位/下一位）；下窄处 = **本人计时**。
- 右上：「查看会议纪要」+「设置」。

**左树**：部门一级（⇅可跨组拖拽排序），个人二级（仅部门内拖拽排序），项目三级（点击切换右侧详情）。顶部查找框过滤。

**右详情**：页头信息区固定不滚动；下方进展详情区滚动、可编辑（全字段）。

**翻页/切换语义**：「下一位」跳到下一个人的第一个项目；跨完一个人的最后一个项目后跳到下一个人；个人内多个项目用左树点击或键盘切换。

---

## 5. 前端架构

### 5.1 路由
- 新增顶层路由 `/meeting-report`（`meta.public` 不设 → 需登录），**置于 AppLayout 之外**实现真全屏。参照 [router/index.ts:7-18](../../../frontend/src/router/index.ts) 顶层写法。

### 5.2 组件树（单一职责）
- `views/MeetingReportView.vue` —— 页面外壳，组装顶栏/左树/右详情，持有 store。
- `components/meeting-report/MeetingTopBar.vue` —— 梯形主席台、双计时显示、汇报人翻页、纪要/设置按钮。
- `components/meeting-report/MeetingReportTree.vue` —— 两级拖拽树 + 查找（查找复用 `projectSearchBlob` 思路）。
- `components/ProjectDetailContent.vue` —— **从 `ProjectDetailDrawer.vue` 抽出的共享内容主体**（详见 5.3）。
- `stores/meetingReport.ts` —— 新增 Pinia store：汇报顺序、计时状态、当前选中项目、设置（总时长/阈值）。与现有 `stores/meeting.ts`（次数/active）职责分离。

### 5.3 详情组件共享（重构 ProjectDetailDrawer）
- 把 `ProjectDetailDrawer.vue` 的**内容主体**（页头信息 + 进展列表 + 编辑/批注/附件逻辑）抽到 `ProjectDetailContent.vue`。
- `ProjectDetailDrawer.vue` 重构为「`el-drawer` 壳 + `<ProjectDetailContent>`」，对外行为、props/emit 保持不变。
- 会议页右栏直接使用 `<ProjectDetailContent>`，配置为"页头固定 + 进展区滚动"的布局变体（通过 prop 控制，如 `layout="meeting"`）。
- **回归风险点**：该组件 1000+ 行，被 [ProjectBoardView.vue](../../../frontend/src/views/ProjectBoardView.vue)、[ProjectOverviewView.vue](../../../frontend/src/views/ProjectOverviewView.vue) 使用（无覆盖测试）。重构后必须手工验证抽屉在总览/看板的原有行为不变（编辑、批注、附件、历史 tab、保存刷新）。

### 5.4 拖拽
- 复用 [TaskBoardView.vue:216-244](../../../frontend/src/views/TaskBoardView.vue) 的原生 HTML5 拖拽（`draggable` + `onDragStart/onDrop` + 乐观更新），不引第三方库。
- 部门级：跨组重排部门顺序。个人级：仅组内重排。每次拖拽结束即保存顺序到后端。

---

## 6. 数据模型与分组

### 6.1 数据获取
- `projectApi.list()` 拉全量 → 前端过滤 `status ∈ {planned, in_progress, paused}`。

### 6.2 分组规则
- 一级按 `project.department`（用 `findDepartment` 容错映射全称/简称）。无部门 → "未分配部门"。
- 二级按 `project.owner_name`。无负责人 → "未分配"。
- "未分配部门""未分配"恒排在各自层级末尾。
- **已知限制（接受）**：部门挂在项目上而非人上。同一负责人若有分属不同部门的项目，会在多个部门下各出现一次（按项目归属）。符合"部门-个人"读法。

### 6.3 排序应用
- 读取后端已存顺序套用。
- 顺序中不存在的新部门/新人，按 紧急度（重要在前）→ 姓名 兜底排到末尾。

---

## 7. 汇报顺序持久化

- **存储**：后端 `SystemSetting`，`key = "meeting_report_order"`，`value` = JSON 字符串。复用 `get_setting/set_setting`。
- **结构**：
  ```json
  {
    "departments": ["研发部", "市场部", "未分配部门"],
    "members": {
      "研发部": ["张三", "李四"],
      "市场部": ["王五"]
    }
  }
  ```
- **API**（新增于 [api/v1/settings.py](../../../backend/api/v1/settings.py)）：
  - `GET /settings/meeting-report-order` → `{ order: {...} }`（管理员可读，普通成员可读以正确排序）
  - `PUT /settings/meeting-report-order` `{ order: {...} }` → 保存（管理员）
- **时机**：拖拽结束即 PUT 保存；本次会议立即生效，下次进入默认沿用。

---

## 8. 计时模型（纯前端运行时）

- 全部在 `stores/meetingReport.ts` 用 `setInterval`(1s) 驱动，不入库。刷新页面则重置（接受）。
- **总计时**：倒计时。总时长默认 30 分钟，可在"设置"调整并存 `SystemSetting`（`key="meeting_total_minutes"`）。归零 → 顶栏总时间区**变红 + 闪烁 + 提示音**。
- **单人计时**：切换汇报人时，上一人时间冻结、新一人从 0 起算。超过**单人统一阈值**（默认 5 分钟，可设，`key="meeting_person_threshold_minutes"`）→ 梯形本人计时**变红 + 闪烁 + 提示音**。
- **提示音**：用 Web Audio 简单蜂鸣（无需音频文件）。
- 切换汇报人触发点：梯形左右箭头 / 点左树的人或项目。

---

## 9. 后端改动（少量）

1. **MeetingRecord 加两列**：`started_at`、`ended_at`（`DateTime`, nullable）。需 1 个 Alembic 迁移。位置 [backend/models/meeting_record.py](../../../backend/models/meeting_record.py)。
2. **会议起止写入**（方案已定，不再二选一）：
   - "开始汇报"→ 新增端点 `POST /meeting-records/{session}/start-report`（管理员）：给当前 active 记录写 `started_at`（仅首次写入，已存在则不覆盖），记操作日志。
   - "结束会议"→ **复用现有 `close_meeting`**：在其归档+关 active 的流程内，对 active 记录补写 `ended_at`，记操作日志。**不新增 end-report 端点。**
3. **会议主要信息日志**：用 `OperationLogService.log()` 记 `action="meeting_report"`，描述如"开始第23次周会汇报"/"结束·时长28分·汇报12项"。
4. **设置项**：总时长、单人阈值、汇报顺序均存 `SystemSetting`，加对应 GET/PUT。
5. 计时数据**不入库**。

---

## 10. 会议生命周期与权限

- **入口**：此页是周会已开启后的"汇报模式"。从现有"开启周会"后进入，或顶部入口直达 `/meeting-report`。
- **权限**：进入与编辑沿用现有 `get_current_admin` / 项目编辑权限（与 [meeting_records.py](../../../backend/api/v1/meeting_records.py)、抽屉一致）。普通成员可看不可改。
- **开始/结束**：
  - "开始汇报"：写 `started_at` + 记日志 + 启动前端计时。
  - "结束会议"：写 `ended_at` + 记日志 + 停计时；可选跳转"查看会议纪要"（现有 `send` 流程，生成飞书文档并分享核心群）。

---

## 11. 风险与回归

| 风险 | 影响 | 缓解 |
|------|------|------|
| 抽离 `ProjectDetailContent` 破坏现有抽屉 | 总览/看板编辑功能回归 | 重构后逐项手工验证（编辑/批注/附件/历史/保存刷新）；保持 props/emit 不变 |
| 全屏页绕过 AppLayout 导致鉴权/登录态缺失 | 未登录可访问 | 路由仍走 `beforeEach` 守卫（非 public） |
| MeetingRecord 加列迁移 | 历史数据 | nullable 列 + Alembic 迁移，旧数据 NULL 兼容 |
| 同一人跨部门多次出现 | 汇报时重复 | 已知限制，按项目归属，会议中可接受 |
| 计时刷新重置 | 误刷新丢计时 | 接受（YAGNI）；可加"刷新确认"提示 |

---

## 12. 测试策略

- **后端**：
  - MeetingRecord 起止时间写入（start-report/end-report 或 close 写 ended_at）单测。
  - 汇报顺序 GET/PUT、计时设置 GET/PUT 的 API 测试（参照 [test_settings_api.py](../../../backend/tests/test_settings_api.py)）。
  - 操作日志记录验证。
- **前端**（手工为主，项目当前无前端单测）：
  - 抽屉在总览/看板回归验证（重点）。
  - 会议页：分组与排序正确、拖拽改顺序并持久化、翻页切换、计时与超时提示、全字段编辑保存。

---

## 13. 默认假设（已在讨论中带入，未被否决）

1. 范围仅 `planned/in_progress/paused` 三态。
2. 无负责人 → "未分配"组，排末尾；无部门 → "未分配部门"，排末尾。
3. 入口与编辑权限与现有管理员/项目权限一致。
4. 总时长默认 30 分钟、单人阈值默认 5 分钟，均可设。
5. 计时为纯前端运行时，不持久化。

---

## 14. 交付物清单

**前端**
- `frontend/src/views/MeetingReportView.vue`（新增）
- `frontend/src/components/meeting-report/MeetingTopBar.vue`（新增）
- `frontend/src/components/meeting-report/MeetingReportTree.vue`（新增）
- `frontend/src/components/ProjectDetailContent.vue`（抽出）
- `frontend/src/components/ProjectDetailDrawer.vue`（重构为壳）
- `frontend/src/stores/meetingReport.ts`（新增）
- `frontend/src/router/index.ts`（加路由）
- `frontend/src/api/resources.ts`（加顺序/计时设置接口）
- `frontend/src/types.ts`（加相关类型）

**后端**
- `backend/models/meeting_record.py`（加 started_at/ended_at）
- `backend/alembic/versions/*`（迁移）
- `backend/services/meeting_record_service.py`（start-report 写 started_at；close_meeting 补写 ended_at）
- `backend/api/v1/meeting_records.py`（新增 start-report 端点；结束复用现有 close）
- `backend/api/v1/settings.py` + `backend/services/settings_service.py`（顺序/计时设置）
- `backend/schemas/*`（对应 schema）
- `backend/tests/*`（对应测试）
