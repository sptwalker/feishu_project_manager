FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# 工作目录设为 /app/backend，使代码以 `backend` 包形式被导入（PYTHONPATH=/app）
WORKDIR /app/backend

# 先装依赖（利用层缓存）
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码到 /app/backend
COPY . /app/backend

# 入口脚本：先迁移再启动
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 数据目录（挂载卷）与非 root 用户
RUN mkdir -p /data && \
    adduser --disabled-password --gecos '' --uid 1000 appuser && \
    chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
