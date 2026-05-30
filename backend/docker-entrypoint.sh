#!/bin/sh
# 容器入口：先执行数据库迁移，再启动传入的命令（默认 uvicorn）
set -e

cd /app/backend

echo "[entrypoint] Running database migrations (alembic upgrade head)..."
alembic upgrade head

echo "[entrypoint] Starting application: $*"
exec "$@"
