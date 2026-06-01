# 阶段总结 2026-06-01（下午）：进展批注/附件 · 日期校验 · 飞书机器人催办

接续上午的「全量清理」阶段，本段围绕**项目详情交互增强**与**飞书机器人定时催办**两条主线推进，并完成外网部署的飞书回调配置更新。

---

## 一、项目进展详情交互增强

### 1. 进展记录批注 / 回复
- 数据模型：`ProgressEntry` 新增 `annotations`（批注）字段；新增 `Annotation`（≤256 字）、`AnnotationReply`（≤128 字）schema 与 TS 类型。批注存于 `progress_log` JSON 内，无需新表/迁移。
- 交互：展示态**右键进展记录**弹出批注输入框；**右键批注框**弹出回复输入框。批注显示作者+时间+内容，回复缩进显示；一条批注可容纳多条回复。
- 作者名：取当前登录用户 `name_en`（英文名），缺失时回退中文名 `name`。
- 修复要点：
  - 批注/回复保存后刷新丢失 → `saveAnnotation` 深拷贝 `progress_log` 再提交。
  - 进入/退出编辑模式丢失批注 → `enterProgressEdit`/`sync` 改用深拷贝；`cleanDraft` 保留 `annotations`。

### 2. 飞书文档链接附件
- 数据模型：`ProgressEntry` 新增 `attachments`；新增 `DocumentAttachment`（url/title/added_at）schema 与 TS 类型。
- 交互：编辑态每行进展右侧「文档」按钮 → 对话框粘贴飞书文档链接 → 正则校验格式（`https://*.feishu.cn/(docx|docs|wiki|base|mindnote|file|drive)/...`）→ 附件显示在进展下方，可点击打开、可删除。
- 修复要点：
  - 退出编辑后附件不显示 / 编辑态点击对话框误触发退出 → `onDocClick` 弹层排除列表加入 `.el-dialog`、`.el-overlay-dialog`（注意**不能用 `.el-overlay`**，否则会匹配抽屉自身遮罩导致无法退出编辑）。
  - `cleanDraft` 保留 `attachments`。

### 3. 进展时间日期校验
- 日期选择器加 `disabled-date` 禁选未来整天。
- 保存前精确到分钟校验：`commitProgress` / `saveCreate` / `onVisible` 三处入口均检查，存在晚于当前时刻的进展则提示错误并阻止保存/关闭，编辑内容不丢失。
- 提示文案："点击下方区域编辑" → "点击下方区域编辑，右键点击记录可添加批注"。

---

## 二、飞书机器人项目进展催办

### 需求
飞书机器人每天定时扫描项目进展，对**进展停滞**或**存在未闭合待办**的项目在群里催办相关负责人。

### 架构（内部服务直查，不开 HTTP 接口）
```
APScheduler 每天 PROJECT_FOLLOWUP_HOUR:MINUTE（默认 09:30）
  └─ scheduler_jobs.job_project_followups
       └─ ProjectFollowupService.send_project_followups
            ├─ find_at_risk_projects(db)      ← 判定逻辑（后端实现，与前端总览同口径）
            ├─ resolve_owner_feishu_id(name)  ← 负责人姓名→飞书ID（过渡方案）
            └─ NotificationService.notify_project_followups → 飞书群催办卡片
```

### 催办判定口径（与前端 `ProjectOverviewView.vue` 同源）
- **进展停滞**：最新 `progress_log.time` 距今 ≥ 阈值天数（默认 30，可在系统设置覆盖）。
- **无进展记录**：在跟踪项目（planned/in_progress/paused）从未有进展。
- **未闭合待办**：存在 pending 状态（待讨论/待确认/待执行）、非反馈本身（无 `reply_to`）、且 id 未被任何 `reply_to` 引用的条目。已完成/取消项目排除。

### 负责人 ↔ 飞书账号「过渡方案」
当前项目 `owner_name` 是与账号解耦的纯姓名字符串（解耦原因：开发期用户账号尚未建立）。
`resolve_owner_feishu_id` 用姓名（先中文名 `name`、再英文名 `name_en`）反查已注册用户拿 `feishu_user_id`：
- 解析到 → 卡片用 `<at id="...">` 真正 @ 个人。
- 解析不到 → 退化为正文文字 `**@姓名**`，保证不漏发。
> **未来计划**：用户账号正式建立后，将项目数据与用户账号关联，届时 `resolve_owner_feishu_id` 改为直接读关联字段即可，上层逻辑不变。

### 新增/修改文件
| 文件 | 说明 |
|---|---|
| `backend/services/project_followup_service.py`（新增） | 催办核心：判定函数 + 编排 + 姓名解析 + 阈值读取 |
| `backend/utils/feishu_cards.py` | 新增 `build_project_followup_card`、`_owner_mention` |
| `backend/services/notification_service.py` | `_send_card` 支持 `receive_id_type`；新增 `notify_project_followups`（发群 chat_id） |
| `backend/services/scheduler_jobs.py` | 新增 `job_project_followups` |
| `backend/core/scheduler.py` | 注册 `project_followups` 定时作业 |
| `backend/core/config.py` | 新增 `PROJECT_FOLLOWUP_HOUR/MINUTE`、`FEISHU_PROJECT_GROUP_CHAT_ID` |
| `backend/schemas/setting.py` | 新增 `FollowupStallDaysResponse/Update` |
| `backend/api/v1/settings.py` | 新增 `GET/PUT /settings/followup-stall-days` |
| `frontend/src/api/resources.ts` | 新增 `getFollowupStallDays/setFollowupStallDays` |
| `frontend/src/components/OtherSettings.vue` | 新增「项目进展催办设置」卡片（停滞天数） |
| `backend/tests/test_project_followup.py`（新增） | 17 个测试 |

### 安全设计
全程受 `SCHEDULER_ENABLED` + `FEISHU_NOTIFY_ENABLED` 双开关保护，**默认关闭**，不会误发。判定逻辑前后端同口径，避免"前端显示要催、机器人不催"的不一致。

---

## 三、配置说明（部署/接入时使用）

### 1. 外网回调更新
`FEISHU_REDIRECT_URI` 已改为 `http://pms.youdoogo.com/api/v1/auth/feishu/callback`。
> 飞书开放平台「安全设置 → 重定向 URL」需把该地址加入白名单，否则登录回调被拒。

### 2. 催办相关 `.env` 配置项
> `.env` 已被 `.gitignore`，App Secret 等密钥不入库。以下为字段说明，实际值在服务器 `.env` 填写。

```ini
# 飞书应用（机器人能力挂在应用上，登录与机器人复用同一应用）
FEISHU_APP_ID=<应用 App ID>
FEISHU_APP_SECRET=<应用 App Secret>

# 催办目标飞书群（chat_id）
FEISHU_PROJECT_GROUP_CHAT_ID=oc_c4f84ea5cbc237fe0a7d731ce5b079eb

# 安全闸（默认 False；两者都为 True 催办才会自动外发）
SCHEDULER_ENABLED=True
FEISHU_NOTIFY_ENABLED=True

# 催办触发时间与阈值（可选，有默认值）
PROJECT_FOLLOWUP_HOUR=9
PROJECT_FOLLOWUP_MINUTE=30
```

停滞催办天数阈值默认 30，存于系统设置表（key=`followup_stall_days`），可在前端「系统设置 › 其他设置 › 项目进展催办设置」由管理员修改，无需改 `.env`。

### 3. 飞书开放平台后台配置清单（接入机器人）
采用**单应用方案**：登录与机器人复用「周例会项目管理工具」这一个应用。
1. 「凭证与基础信息」获取 App ID / App Secret。
2. 「添加应用能力 → 机器人」启用机器人能力。
3. 「权限管理」开通 `im:message`、`im:message:send_as_bot`、`im:chat`。
4. 将机器人**拉进目标群** `oc_c4f84ea5...`（否则无法发群消息）。
5. （未来收群内指令时）「事件订阅」请求地址填 `http://pms.youdoogo.com/api/v1/feishu/webhook`，记录 Verification Token / Encrypt Key。
6. 「版本管理与发布」创建版本并发布——**权限变更须发布后才生效**。

### 4. 上线验证顺序
1. 连通性测试：调 `feishu_client.send_card(chat_id, card, receive_id_type="chat_id")` 往群发测试卡片。
2. 催办全链路：手动触发 `ProjectFollowupService.send_project_followups` 看群里是否收到催办卡片。
3. 确认无误后依赖每日定时任务自动运行。

### 5. 常见报错
| 报错 | 原因 |
|---|---|
| `Failed to get tenant access token` | App ID/Secret 错，或未发布版本 |
| 发消息权限错误 / bot not in chat | 机器人没拉进群，或 `im:message` 未发布 |
| 群里收不到但日志无错 | `FEISHU_NOTIFY_ENABLED` 仍为 False |
| 定时任务不跑 | `SCHEDULER_ENABLED` 仍为 False |

---

## 四、测试与验证
- 后端 `pytest`：**247 通过 / 1 警告**（新增 `test_project_followup.py` 17 项、`test_annotation_feature.py` 5 项；修正 `test_scheduler` 的 job_ids 断言加入 `project_followups`）。
- 前端 `vue-tsc + vite build`：零错误。
- 连续 5 次全量跑测试稳定通过（修复了 `test_scheduler` 的 `asyncio.run` 关闭事件循环污染后续 task_api 异步用例的顺序敏感问题）。

---

## 五、后续可选项 / 已知技术债
- **接收群内指令/事件**：webhook 入口 `feishu_webhook.py` 的 `_dispatch_event` 当前仅记录日志，未做业务分发。未来做"群里 @机器人 触发催办/查询"需补事件解析 + 指令路由 + 回消息（独立立项）。
- **项目数据与用户账号关联**：当前为姓名字符串过渡方案，待账号体系完善后正式关联。
- 飞书机器人需在开放平台开通权限并发布、拉群后方可真实外发。
- `BaseSettings` 的 `class Config` 弃用警告（低优先，等 pydantic-settings 指引明确再迁移）。
