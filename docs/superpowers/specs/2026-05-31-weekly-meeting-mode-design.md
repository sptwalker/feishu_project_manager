# 周例会记录模式 — 设计文档

- 日期：2026-05-31
- 状态：已确认，进入实现

## 背景

公司周例会期间，需要一个全局"周例会记录状态"，让项目进展记录被标记为某次周会的记录，便于识别与未来统计。现有系统无全局配置存储。

## 已确认决策

1. 周例会状态 = **公司级全局状态**（所有人共享、跨会话持久）。
2. 记录标记 = **结构化字段**（`ProgressEntry.meeting_session`），显示时渲染前缀，统计按字段查询。
3. 周会次数 = **按自然周递增**：同一自然周次数恒定，跨到新的一周自动 +1；基准 `2026-06-01`（周一）= 第 22 次；管理员可手动校准。
4. 顶部开关对**非管理员只读显示**当前状态。
5. "其他设置" tab 展示本周/上次周会信息（见 ⑤）。
6. 第 4 点"统计查询界面"本次**不做**，只做数据结构支持（`meeting_session` 字段）。

## ① 数据模型

**新建 `system_settings`（key-value）表**（通用，未来 AI/主题设置可复用）：
- `key` String 唯一、`value` Text（字符串/JSON）、`updated_at`
- 周例会用到的键：`meeting_active`（"true"/"false"）、`meeting_base_monday`（`2026-06-01`）、`meeting_base_count`（`22`）

**`ProgressEntry` 增加可选字段** `meeting_session?: int`（该条所属周会次数）。前后端 type/schema 同步。

## ② 周会次数算法

```
mondayOf(d)      = d 所在自然周的周一
count(d)         = base_count + weeks_between(base_monday, mondayOf(d))
weeks_between    = floor((mondayOf(d) - base_monday).days / 7)
```
- 同一自然周次数恒定，跨周 +1。
- 初始 `base_monday=2026-06-01`、`base_count=22`。
- 校准：管理员设定"即将到来的周会次数"，后端重设 `base_monday`=目标周一、`base_count`=新值。

## ③ 后端 API（新建 `settings` 路由，前缀 `/api/v1/settings`）

- `GET /settings/meeting`（所有登录用户）→
  ```
  {
    active: bool,
    base_monday: str, base_count: int,
    this_week_monday: str, this_week_count: int,
    this_week_recorded: bool,              // 本周是否已有周会记录
    last_meeting: { date: str, count: int } | null,  // 上一次周会
    calibration_count: int,                // 可修改的目标次数（本周未记录=本周次数；已记录=下周次数）
    calibration_monday: str                // 校准对应的周一
  }
  ```
- `PUT /settings/meeting/active`（**仅管理员**）body `{active: bool}` → 开关状态
- `PUT /settings/meeting/count`（**仅管理员**）body `{count: int}` → 以 `calibration_monday` 为基准重设 `base_count`

**周会记录扫描**（用于 `this_week_recorded` 与 `last_meeting`）：遍历各 project 的 `progress_log`，收集带 `meeting_session` 的条目。`this_week_recorded` = 存在 `meeting_session == this_week_count`；`last_meeting` = `meeting_session < this_week_count` 中 session 最大者的 {time, session}。项目量级（百级）下内存遍历可接受。

## ④ 前端状态

新建 Pinia **`meetingStore`**：`active`、`thisWeekCount`、`thisWeekRecorded`、`lastMeeting`、`calibrationCount`、`calibrationMonday` 等；actions：`load()`、`setActive()`、`setCount()`。App 启动/登录后 `load()`。

## ⑤ 各 UI 实现点

1. **AppLayout 顶部**加"周例会"开关：
   - 管理员：`el-switch` 可操作；打开提示 **"现在进入公司管理周例会记录状态"**；登录后若已开启提示 **"现在系统在公司周例会记录状态"**
   - 非管理员：只读显示状态文字（如"周例会记录中"）
2. **ProjectDetailDrawer** 周会模式下右上角蓝色大字 **"周会记录中……"**
3. **进展详情编辑**：周会模式下内容输入框前显示蓝色标签 **"周会记录："**（UI 提示，不存储）
4. **保存进展记录**：周会模式下给该条 `meeting_session` = 当前周会次数；**显示**时带 `meeting_session` 的条目在内容前渲染加粗蓝色 **"【第xx次周会更新】"**
5. **SettingsView 加"其他设置" tab**（OtherSettings 组件）：
   - 本周已召开 → "本周已召开第 N 次周例会" + "下一次（下周）应为第 N+1 次（可修改保存）"
   - 本周未召开 → "上一次周例会：YYYY-MM-DD 第 M 次" + "本周周例会将为第 N 次（可修改保存）"
   - 同时显示下一个工作日周一日期

## ⑥ 权限 / 错误 / 测试

- 开关与次数校准仅管理员（`get_current_admin`），非管理员 403。
- 初始化：首次读取若无配置，写入默认 `active=false`、`base_monday=2026-06-01`、`base_count=22`。
- 测试：后端周会次数计算函数单测、`this_week_recorded`/`last_meeting` 扫描单测、settings API 权限测试；前端手动验证。
