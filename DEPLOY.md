# 腾讯云部署手册（Docker Compose 单机方案）

> 适用：飞书项目管理系统（FastAPI + Vue + SQLite，已 Docker 化）。
> 推荐机型：腾讯云**轻量应用服务器（Lighthouse）** 或 **CVM**，2 核 2G 起步，系统选 Ubuntu 22.04 / Debian 12。

---

## ⚠️ 部署前必读（安全）

1. **立即更换你的腾讯云子账号密码**——它曾以明文出现在对话/文件中。
2. `.env` 里的 `SECRET_KEY`、飞书 `APP_SECRET` 等都是机密，**不要提交到 git、不要外发**。
3. 服务器安全组只开放必要端口：`22`（SSH）、`80`（HTTP）、`443`（如启用 HTTPS）。

---

## 步骤 1：准备服务器

1. 腾讯云购买轻量应用服务器。镜像可直接选「Docker CE」应用镜像；若选纯系统镜像，则登录后装 Docker：
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo systemctl enable --now docker
   # 验证
   docker version && docker compose version
   ```
2. 在轻量服务器「防火墙」/CVM「安全组」放通入站端口 **80**（如做 HTTPS 再加 **443**）。

## 步骤 2：把代码放到服务器

推荐用 Git（便于后续更新）。**注意：本地当前有未提交改动，先在本地提交并推送到远程仓库**（GitHub / Gitee / 腾讯云 Coding 均可）：

```bash
# 本地
git add -A
git commit -m "chore: ready for deploy"
git push origin main
```

服务器上拉取：
```bash
git clone <你的仓库地址> feishu_project_manager
cd feishu_project_manager
```

> 不想用 Git 也可本地打包上传：`scp -r ./feishu_project_manager root@<服务器IP>:/root/`（排除 node_modules、本地 venv）。

## 步骤 3：配置环境变量 `.env`

```bash
cd docker
cp .env.example .env
```

编辑 `.env`，**至少改这几项**：

| 变量 | 改成什么 |
|---|---|
| `SECRET_KEY` | 用 `python3 -c "import secrets;print(secrets.token_hex(32))"` 生成的随机串 |
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` | 你的飞书自建应用凭证 |
| `FEISHU_REDIRECT_URI` | `http://<你的域名或公网IP>/api/v1/auth/feishu/callback` |
| `FRONTEND_URL` | `http://<你的域名或公网IP>`（用于 CORS） |
| `DEBUG` | 保持 `False` |

> 数据库 `DATABASE_URL=sqlite:////data/feishu_pm.db` 不用改（指向容器数据卷，4 个斜杠是绝对路径）。

## 步骤 4（可选）：迁移现有数据

容器首次启动会自动建表（空库）。**若要把本地已有的用户/部门/项目数据带到线上**：

```bash
# 本地：把数据库文件传到服务器
scp backend/data/feishu_pm.db root@<服务器IP>:/tmp/feishu_pm.db
```
```bash
# 服务器：先启动一次创建数据卷，再把文件拷进卷
cd docker && docker compose up -d backend
docker cp /tmp/feishu_pm.db feishu_pm_backend:/data/feishu_pm.db
docker compose restart backend
```
> 不迁移则是全新系统：第一个用飞书登录的人会成为普通成员（`member`），需你进数据库把某人 `role` 改成 `admin`，或参考下方「设管理员」。

## 步骤 5：构建并启动

```bash
cd docker
docker compose up -d --build
```
- 前端构建会自动跑 `vue-tsc + vite build`，后端入口会自动执行数据库迁移。
- 查看状态与日志：
  ```bash
  docker compose ps
  docker compose logs -f
  ```

启动后访问 `http://<你的公网IP>/` 即可看到前端。

## 步骤 6：配置飞书开放平台

在飞书开放平台你的应用里：
- **重定向 URL / 安全域名**：加上 `http://<你的域名或公网IP>`，回调填 `http://<你的域名或公网IP>/api/v1/auth/feishu/callback`（与 `.env` 的 `FEISHU_REDIRECT_URI` 完全一致）。
- 确保应用有获取用户信息（`contact:user.base:readonly` 等）权限。

## 步骤 7：验证

```bash
curl http://<公网IP>/api/v1/health     # 期望 {"status":"healthy"}
```
浏览器打开首页 → 用飞书登录 → 检查项目总览/系统设置等。

## 设管理员（如需）

进后端容器用 sqlite 修改：
```bash
docker exec -it feishu_pm_backend python -c "
from backend.db.session import SessionLocal
from backend.models.user import User, UserRole
db=SessionLocal()
u=db.query(User).filter(User.name=='刘丹').first()
if u: u.role=UserRole.ADMIN; db.commit(); print('done', u.name, u.role.value)
else: print('user not found')
"
```

---

## 步骤 8（可选）：域名 + HTTPS

1. 域名解析 A 记录指向服务器公网 IP（腾讯云域名需备案才能用 80/443）。
2. 推荐在前端容器前加一层带 TLS 的反代，或用腾讯云「SSL 证书」免费证书 + 在宿主机装 Nginx/Caddy 反代到 `127.0.0.1:80`。
3. 启用 HTTPS 后，把 `.env` 的 `FEISHU_REDIRECT_URI`、`FRONTEND_URL` 改成 `https://...`，飞书后台同步改，重启：`docker compose up -d`。

---

## 运维速查

| 操作 | 命令 |
|---|---|
| 更新代码重新部署 | `git pull && cd docker && docker compose up -d --build` |
| 查看日志 | `docker compose logs -f backend` / `frontend` |
| 备份数据库 | `docker cp feishu_pm_backend:/data/feishu_pm.db ./backup-$(date +%F).db` |
| 停止 | `cd docker && docker compose down` |
| 重启 | `cd docker && docker compose restart` |

> 提示：SQLite 适合中小团队。若并发增大，可改用腾讯云 PostgreSQL/MySQL —— 把 `DATABASE_URL` 换成对应连接串，并在 `backend/requirements.txt` 增加驱动后重建镜像。
