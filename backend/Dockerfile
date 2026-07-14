FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    TZ=Asia/Shanghai

# 容器时区设为北京时间：datetime.now() 等按本地(中国)时间，修正留言/日志/周会等时间偏差
# （python:slim 默认 UTC，会导致展示时间比实际早 8 小时）
# apt 换用华为云镜像（同 pip），避免默认 deb.debian.org 在国内极慢导致构建卡住
RUN for f in /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources; do \
        [ -f "$f" ] && sed -i 's|deb.debian.org|mirrors.huaweicloud.com|g; s|security.debian.org|mirrors.huaweicloud.com|g' "$f" || true; \
    done && \
    apt-get update && apt-get install -y --no-install-recommends tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

# 工作目录设为 /app/backend，使代码以 `backend` 包形式被导入（PYTHONPATH=/app）
WORKDIR /app/backend

# 先装依赖（利用层缓存）
COPY requirements.txt ./
RUN pip config set global.index-url https://repo.huaweicloud.com/repository/pypi/simple && \
    pip config set global.trusted-host repo.huaweicloud.com && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

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
