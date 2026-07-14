FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    TZ=Asia/Shanghai

# 工作目录设为 /app/backend，使代码以 `backend` 包形式被导入（PYTHONPATH=/app）
WORKDIR /app/backend

# 先装依赖（利用层缓存）
COPY requirements.txt ./
RUN pip config set global.index-url https://repo.huaweicloud.com/repository/pypi/simple && \
    pip config set global.trusted-host repo.huaweicloud.com && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt tzdata && \
    # 时区=北京时间：用 pip 的 tzdata（走已配置的国内 pip 源，快且稳）把 zoneinfo 拷进系统目录，
    # 使 datetime.now() 按本地(中国)时间。避开 apt（默认 debian 源国内极慢/易失败）。
    SP="$(python -c "import sysconfig;print(sysconfig.get_paths()['purelib'])")" && \
    mkdir -p /usr/share/zoneinfo && cp -r "$SP/tzdata/zoneinfo/." /usr/share/zoneinfo/ && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

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
