# 部署文档

## 生产环境部署

### 1. 服务器要求

- 操作系统: Ubuntu 20.04+ / CentOS 7+
- Docker: 20.10+
- Docker Compose: 2.0+
- 内存: 最低2GB，推荐4GB
- 磁盘: 最低10GB可用空间

### 2. 部署步骤

#### 2.1 安装Docker

```bash
# Ubuntu
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2.2 克隆项目

```bash
git clone https://github.com/sptwalker/feishu_project_manager.git
cd feishu_project_manager
```

#### 2.3 配置环境变量

```bash
cd docker
cp .env.example .env
vim .env
```

必须配置的变量:
- `JWT_SECRET_KEY`: 生成随机密钥（至少32字符）
  ```bash
  # 使用openssl生成
  openssl rand -hex 32
  # 或使用Python生成
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- `FEISHU_APP_ID`: 飞书应用ID
- `FEISHU_APP_SECRET`: 飞书应用密钥
- `FEISHU_VERIFICATION_TOKEN`: 飞书验证令牌
- `FEISHU_ENCRYPT_KEY`: 飞书加密密钥（如果飞书应用启用了消息加密，则必须配置）

#### 2.4 启动服务

```bash
docker-compose up -d
```

#### 2.5 查看日志

```bash
docker-compose logs -f
```

### 3. 反向代理配置（可选）

如果需要使用域名访问，可以配置Nginx反向代理:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. 数据备份

```bash
# 备份SQLite数据库
docker-compose exec backend cp /app/data/feishu_pm.db /app/data/backup_$(date +%Y%m%d).db

# 复制到宿主机
docker-compose cp backend:/app/data/backup_$(date +%Y%m%d).db ./
```

### 5. 更新部署

```bash
git pull
cd docker
docker-compose down
docker-compose build
docker-compose up -d
```

## 故障排查

### 后端无法启动

1. 检查日志: `docker-compose logs backend`
2. 检查环境变量配置
3. 检查数据库文件权限

### 前端无法访问

1. 检查容器状态: `docker-compose ps`
2. 检查nginx配置
3. 检查后端API是否正常

### 飞书集成失败

1. 验证飞书应用配置
2. 检查回调地址是否正确
3. 查看后端日志中的飞书API调用错误
