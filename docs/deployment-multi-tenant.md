# 多租户外网部署手册（pms / sales 双实例）

> 适用：飞书项目管理系统（FastAPI + Vue + SQLite，已 Docker 化）的**多实例 white-label** 部署。
> 一份前端 + 多个后端，按子域名分流；本手册以 `pms.youdoogo.com`（产品）+ `sales.youdoogo.com`（营销）两实例为例。
> 单实例简易部署见 [DEPLOY.md](../DEPLOY.md)；本手册覆盖多租户场景。

---

## 一、架构总览

```
                          公网 HTTPS (443)
                               │
                  ┌────────────┴─────────────┐
                  │  外层反代/负载均衡 (终止TLS) │   ← 生产必需，见步骤 6
                  └────────────┬─────────────┘
                               │ HTTP → 服务器:8088
                    ┌──────────┴──────────┐
                    │  frontend (Nginx)    │  同一份 dist，按 server_name 分流
                    └──┬───────────────┬───┘
       pms.youdoogo.com│               │sales.youdoogo.com
                       ▼               ▼
              backend (产品)     backend-sales (营销)
              backend_data 卷    sales_data 卷         ← 数据物理隔离
              .env               .env.sales           ← 各自密钥/飞书应用/品牌
```

关键设计（对应仓库文件）：

| 设计点 | 来源文件 |
|---|---|
| 两后端复用同一镜像、独立数据卷、独立 `.env*` | [docker/docker-compose.yml](../docker/docker-compose.yml) |
| Nginx 按 `server_name` 分流到不同后端，按子域名映射 `/branding/` | [frontend/nginx.conf](../frontend/nginx.conf) |
| 每实例独立 `SECRET_KEY` / 飞书应用 / 品牌项 | [docker/.env.sales.example](../docker/.env.sales.example) |
| 品牌差异化（logo/标题/配色/文案）由 `/api/v1/branding` 返回，前端启动应用 | [backend/api/v1/branding.py](../backend/api/v1/branding.py) |
| 数据库迁移容器启动时自动跑 `alembic upgrade head` | [backend/docker-entrypoint.sh](../backend/docker-entrypoint.sh) |

> ⚠️ **数据隔离与安全**：两实例数据各在独立卷，互不可见；但**必须用不同的 `SECRET_KEY`**，否则两边 JWT 互认 = 越权。每实例用**各自的飞书应用**（`open_id` 按应用恒定，故初始管理员名单也不同）。

---

## 二、前置准备

1. **服务器**：2 核 2G 起，Ubuntu 22.04 / Debian 12；安装 Docker + Compose：
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo systemctl enable --now docker
   docker version && docker compose version
   ```
2. **DNS**：两条 A 记录都指向服务器公网 IP：
   - `pms.youdoogo.com` → 服务器IP
   - `sales.youdoogo.com` → 服务器IP
3. **两个飞书自建应用**：产品方一个、营销方一个；各拿到 `App ID / App Secret`，记下各自管理员的飞书 `open_id`。
4. **安全组放通**：`22`(SSH)、`80`、`443`。

---

## 三、拉代码 + 配置环境变量

```bash
git clone <你的仓库> feishu_project_manager
cd feishu_project_manager/docker
```

### 3.1 产品实例 `.env`

```bash
cp .env.example .env
```

编辑 `.env`，必改项：

| 变量 | 值 |
|---|---|
| `SECRET_KEY` | `openssl rand -hex 32` 生成（**产品实例专用**） |
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` | 产品方飞书应用凭证 |
| `FEISHU_REDIRECT_URI` | `https://pms.youdoogo.com/api/v1/auth/feishu/callback` |
| `FRONTEND_URL` | `https://pms.youdoogo.com`（CORS 用） |
| `SYSTEM_PUBLIC_URL` | `https://pms.youdoogo.com/`（通知跳转链接用） |
| `INITIAL_ADMIN_FEISHU_IDS` | `["ou_产品方管理员openid"]` |
| `DEBUG` | `False` |

> `DATABASE_URL=sqlite:////data/feishu_pm.db` 保持不变（4 个斜杠，指向容器数据卷）。

### 3.2 营销实例 `.env.sales`

```bash
cp .env.sales.example .env.sales
```

`.env.sales.example` 已标好"必须与产品不同"的项，逐项填：

- `SECRET_KEY=` **另生成一个**（`openssl rand -hex 32`，**绝不能与产品相同**）
- `FEISHU_APP_ID/SECRET=` 营销方应用凭证
- `FEISHU_REDIRECT_URI=https://sales.youdoogo.com/api/v1/auth/feishu/callback`
- `FRONTEND_URL=https://sales.youdoogo.com`
- `SYSTEM_PUBLIC_URL=https://sales.youdoogo.com/`
- `INITIAL_ADMIN_FEISHU_IDS=["ou_营销方管理员openid"]`
- `BRAND_*` 品牌项（模板已给橙色营销主题示例，按需替换）

> `.env` 与 `.env.sales` 均已被 `.gitignore`，不会进仓库——密钥安全。

### 3.3 品牌差异化变量速查（BRAND_*）

| 变量 | 含义 |
|---|---|
| `BRAND_SIDEBAR` | 侧边栏品牌名（支持 HTML，`class="brand-accent"` 高亮） |
| `BRAND_LOGIN` / `BRAND_MARK` | 登录页品牌名 / 左上方块标记字符 |
| `BRAND_PAGE_TITLE` | 浏览器标签标题 |
| `BRAND_LOGIN_HEADLINE` / `BRAND_LOGIN_SUB` | 登录页主/副标语（支持 HTML） |
| `BRAND_LOGO_URL` / `BRAND_FAVICON_URL` | logo / favicon 路径（指向 `/branding/...`） |
| `BRAND_ACCENT` / `_HOVER` / `_SOFT` | 主题强调色（留空沿用产品默认蓝） |
| `BRAND_SIDEBAR_BG` / `_HOVER` | 侧边栏背景/悬停色 |

---

## 四、放品牌图片

把各实例的 logo / favicon 放到对应目录（Nginx 按子域名映射到 `/branding/`，见 compose 只读挂载）：

```
docker/branding/pms/logo.png          # 产品方（可留空，用前端内置默认）
docker/branding/sales/logo.png        # 营销方（.env.sales 已配 /branding/logo.png）
docker/branding/sales/favicon.svg
```

---

## 五、构建并启动

```bash
cd docker
docker compose up -d --build
```

- 前端镜像构建跑 `vue-tsc + vite build`；两个后端容器启动时**自动执行 `alembic upgrade head`**（含全部迁移）。
- `frontend` 依赖**两个后端都 healthy** 才启动（compose `depends_on`）——所以 `.env` 与 `.env.sales` **都必须存在**。

查看状态与日志：
```bash
docker compose ps
docker compose logs -f
```

---

## 六、外层 HTTPS 反代（生产关键，飞书 OAuth 必需 HTTPS）

容器 Nginx 只监听 80，compose 映射到主机 **8088**；`nginx.conf` 注释明确"**生产 TLS 在更外层终止**"。生产拓扑：**外层反代终止 TLS(443) → 转发到容器的 8088**。

**推荐 Caddy（自动签发/续期 Let's Encrypt 证书）**。主机装 Caddy，`/etc/caddy/Caddyfile`：

```caddyfile
pms.youdoogo.com, sales.youdoogo.com {
    reverse_proxy localhost:8088 {
        header_up Host {host}              # 关键：透传 Host，容器 Nginx 才能按子域名分流
        header_up X-Forwarded-Proto https
    }
}
```

```bash
sudo systemctl reload caddy
```

> `header_up Host {host}` 必须保留——容器内 Nginx 靠 Host 头区分 pms / sales；丢失会导致 sales 流量错走默认的 pms 后端。
>
> 替代方案：腾讯云 **CLB** 终止 TLS 转发到 8088；或容器 Nginx 直接加 443+证书（需改 nginx.conf 与 compose 端口映射，较繁琐，不推荐）。

---

## 七、配置两个飞书应用后台

对**每个**飞书应用分别配置（产品应用配 pms，营销应用配 sales）：

- **重定向 URL**：`https://{子域名}/api/v1/auth/feishu/callback`，**与对应 .env 的 `FEISHU_REDIRECT_URI` 完全一致**。
- **安全域名**：加 `https://{子域名}`。
- **权限**：获取用户信息（`contact:user.base:readonly` 等）。
- 如需真实发周会通知/催更：该应用还需消息权限，并把机器人拉进核心群（chat_id 在「系统设置 › 其他设置」配；真实外发还受 compose 里 `FEISHU_NOTIFY_ENABLED=True` 控制）。

---

## 八、设管理员

初始管理员靠 `INITIAL_ADMIN_FEISHU_IDS`——名单内成员**首次飞书登录即自动成为 admin**。若漏配可手动设：

```bash
# 产品实例
docker exec -it feishu_pm_backend python -c "
from backend.db.session import SessionLocal
from backend.models.user import User, UserRole
db=SessionLocal(); u=db.query(User).filter(User.name=='某人').first()
u and (setattr(u,'role',UserRole.ADMIN), db.commit())"

# 营销实例：容器名换成 feishu_pm_backend_sales
```

---

## 九、验证

```bash
curl https://pms.youdoogo.com/api/v1/health       # {"status":"healthy"}
curl https://sales.youdoogo.com/api/v1/health
curl https://sales.youdoogo.com/api/v1/branding    # 看营销品牌配置是否返回
```

浏览器分别打开两个子域名 → 各自 logo/标题/配色不同 → 飞书登录 → 验证两实例数据互相隔离。

---

## 十、关键避坑清单

| 坑 | 后果 / 处理 |
|---|---|
| 两实例用了相同 `SECRET_KEY` | **越权**：A 的 token 能登 B。务必各生成一个 |
| 外层反代没透传 `Host` 头 | 容器 Nginx 无法分流，sales 流量错走默认的 pms 后端 |
| `FEISHU_REDIRECT_URI` 与飞书后台不一致 | 登录回调失败（最常见报错） |
| 缺 `.env.sales` | `backend-sales` 起不来 → frontend 因 `depends_on` 也不启动 |
| 用了 HTTP 而非 HTTPS | 飞书 OAuth 多数场景要求 HTTPS；务必配好步骤六 |

---

## 十一、升级与维护

```bash
cd feishu_project_manager
git pull
cd docker
docker compose up -d --build      # 迁移自动跑；SQLite 数据在卷里不丢
```

数据备份：两实例数据分别在 Docker 卷 `backend_data` / `sales_data`；也可在各实例「系统设置 › 其他设置 › 数据备份」导出 JSON 快照。

---

## 附：仅上单实例的差异（备忘）

本手册为双实例。若临时只上产品实例：在 [docker-compose.yml](../docker/docker-compose.yml) 删除 `backend-sales` 服务及 `frontend.depends_on` 中的 `backend-sales` 项、移除 `sales_data` 卷与 sales 品牌挂载，并删除 [nginx.conf](../frontend/nginx.conf) 中 sales 的 `server` 块。本次部署为**双实例全量**，无需此操作。
