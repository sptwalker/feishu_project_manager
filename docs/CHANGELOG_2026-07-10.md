# 阶段总结 2026-07-10：外部留言讨论区（独立公开模块）

本阶段交付一个**面向外部用户的公开留言讨论区**：外部用户免飞书、通过邮箱验证码注册后留言（文字/图片/视频），内部飞书用户在管理页查看、搜索、回复并评定奖励星级。与 PM 项目管理**完全隔离**（独立数据库/媒体目录/外部 JWT），仅借用域名、部署容器、内部飞书登录。

提交：后端 `c7726be`、前端 `a1d9c01`。

---

## 一、架构与隔离边界

- **自治包 [backend/discuss/](backend/discuss/)**：db / models / service / api 自成一包，不 import 任何 project/meeting 模块。
- **数据物理隔离**：独立 `discuss.db`（第二 SQLAlchemy 引擎，[discuss/db.py](backend/discuss/db.py) 惰性建表，不入主库 alembic 链）；媒体存独立 `discuss_uploads/` 目录。PM 的备份/导入/乐观锁/迁移完全不感知本模块。
- **外部身份隔离**：外部用户 JWT 用主 SECRET_KEY 经 HMAC 派生的独立密钥 + `aud=discuss` 签发（[service.py](backend/discuss/service.py)），与内部 token **互不相认**（有单测证明）；前端存 `dsc_token`，与内部 `fpm_access_token` 完全分离。
- 配置新增（[config.py](backend/core/config.py)）：`DISCUSS_DATABASE_URL` / `DISCUSS_UPLOAD_DIR` / `DISCUSS_IMAGE_MAX_MB=10` / `DISCUSS_VIDEO_MAX_MB=100` / `DISCUSS_TOKEN_EXPIRE_DAYS=30`。

## 二、数据模型（discuss.db，4 表，[models.py](backend/discuss/models.py)）

- `discuss_users`：邮箱(唯一)/手机号/昵称/status(active|blocked)/注册IP哈希。
- `discuss_codes`：验证码哈希/过期/错误次数/冷却与每日计数（不存明文码）。
- `discuss_boards`：v1 单讨论区（标题/欢迎语/开闭）；留言按 board_id 关联，未来多区零迁移。
- `discuss_messages`：楼结构（thread_id 根自指）/author_type(external|internal)/content(纯文本)/attachments(JSON)/star(0-5)/status(visible|hidden)/replied(未回复筛选冗余标记)。

## 三、后端能力（[service.py](backend/discuss/service.py)、[api.py](backend/discuss/api.py)）

### 外部（公开，部分需外部 token）
- `POST /discuss/code|register|login`：邮箱验证码注册/登录（**无密码**），注册必填昵称+手机号。
- `GET /discuss/board|threads`：讨论区信息与楼列表（公开视图**绝不含邮箱/手机**）。
- `POST /discuss/messages`：发留言（新楼）或**本人楼内补充**（他人楼 403）。
- `POST /discuss/upload`：图片 JPG/PNG≤10MB、视频 MP4≤100MB；扩展名+content-type+**魔数**三重校验；仅注册用户可传；附件 URL 白名单（仅本站 /discuss/media/）。

### 内部（现有飞书 JWT）
- `GET /discuss/admin/threads`：全量列表，支持搜索（内容/昵称/邮箱/手机）、**仅看未回复**、星级过滤；含外部用户资料。
- `POST /discuss/admin/reply`：官方回复（记内部真名，楼标记已回复）。
- `PUT /discuss/admin/star|visibility|block`：1-5 星评定（外部可见）/隐藏恢复/封禁解封。

### 防滥用
- 验证码：60s 冷却、每日≤10 封、5 次错误作废、一次性消费。
- 发帖：1 条/分钟、50 条/天；注册：单 IP 5 账号/天；honeypot 隐藏字段。
- 运行时开关关闭 → 公开接口一律 404（不暴露功能存在）。
- SMTP 未配置 → 验证码降级打印后端日志（本地测试模式），不阻塞开发。

## 四、设置接入（[settings.py](backend/api/v1/settings.py)、[settings_service.py](backend/services/settings_service.py)）

- 「其他设置」新增两卡片：**留言讨论区开关**（运行时，开启→侧栏菜单出现+公开页可访问）、**SMTP 邮件服务器**（host/port/SSL/账号/密码只写不回显/发件人 + 测试邮件按钮）。
- `/branding` 下发 `discuss_enabled`（沿用 sales_code_enabled 模式），控制侧栏菜单与路由。

## 五、前端

- **公开页 [/forum → ForumView.vue](frontend/src/views/ForumView.vue)**：免登录路由、不进 AppLayout；**移动端优先**（390×844 实测）；底部抽屉式登录/注册；发帖含附件预览；图片自适应+点击放大遮罩、视频原生播放器；官方回复蓝底+「官方」徽章；星级 ★ 展示；外部内容**永远纯文本渲染**（绝不 v-html）。
- **内部管理页 [DiscussAdminView.vue](frontend/src/views/DiscussAdminView.vue)**：工具条（搜索/未回复勾选/星级下拉）、楼卡片（未回复黄标、隐藏灰显、邮箱手机可见）、el-rate 评星、回复框、隐藏/封禁（带确认）。
- [resources.ts](frontend/src/api/resources.ts)：`discussApi`（公开端原生 fetch 携带 dsc_token，避开 axios 内部拦截器；管理端走内部实例）+ settings 的 discuss/SMTP 方法。

## 六、测试与验证

- 后端新增 [test_discuss.py](backend/tests/test_discuss.py) 15 例（验证码冷却/作废、IP 限注册、楼结构、他人楼禁止、限流、封禁、replied 标记与未回复筛选、星级、隐藏、公开视图无隐私、搜索、**双 JWT 隔离**）；全量 **446 passed**。
- `vue-tsc` 通过；浏览器端到端：开关 404→开启→注册→发帖→内部页资料/未回复→回复→评星→手机视口截图确认。测试数据已清理、开关恢复默认关。

## 七、部署备忘

- Docker `.env` 增加：`DISCUSS_DATABASE_URL=sqlite:////data/discuss.db`、`DISCUSS_UPLOAD_DIR=/data/discuss_uploads`（均落在现有 backend_data 卷内，自动持久化）。
- 上线步骤：部署 → 管理员在「其他设置」配 SMTP（测试邮件验证）→ 打开留言区开关 → 对外发放链接 `https://<域名>/forum`。
- 待办（P1，未开发）：新留言飞书群通知、侧栏未回复角标；（P2）多讨论区管理 UI（数据模型已就绪）。
