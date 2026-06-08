import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import get_settings
from backend.core.scheduler import start_scheduler, shutdown_scheduler
from backend.api.v1 import auth, projects, tasks, risks, feishu_webhook, bitable, reports, users, departments
from backend.api.v1 import settings as settings_api
from backend.api.v1 import backup as backup_api
from backend.api.v1 import meeting_records as meeting_records_api
from backend.api.v1 import operation_logs as operation_logs_api
from backend.api.v1 import branding as branding_api

settings = get_settings()

# 配置应用日志输出到 stdout（docker logs 可见）。
# 默认 Python 仅输出 WARNING+，会吞掉调度器启动、定时任务执行/跳过等关键 INFO 日志，
# 导致定时任务问题无法从日志排查。force=True 覆盖任何已有 root 配置，确保 backend.* 的日志可见。
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    force=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动/关闭定时任务调度器（受 SCHEDULER_ENABLED 控制）"""
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1")
app.include_router(
    projects.router,
    prefix="/api/v1/projects",
    tags=["projects"]
)
app.include_router(
    tasks.router,
    prefix="/api/v1",
    tags=["tasks"]
)
app.include_router(
    risks.router,
    prefix="/api/v1",
    tags=["risks"]
)
app.include_router(
    feishu_webhook.router,
    prefix="/api/v1",
    tags=["feishu"]
)
app.include_router(
    bitable.router,
    prefix="/api/v1",
    tags=["bitable"]
)
app.include_router(
    reports.router,
    prefix="/api/v1",
    tags=["reports"]
)
app.include_router(
    users.router,
    prefix="/api/v1",
    tags=["users"]
)
app.include_router(
    departments.router,
    prefix="/api/v1/departments",
    tags=["departments"]
)
app.include_router(
    settings_api.router,
    prefix="/api/v1",
    tags=["settings"]
)
app.include_router(
    backup_api.router,
    prefix="/api/v1",
    tags=["backup"]
)
app.include_router(
    meeting_records_api.router,
    prefix="/api/v1",
    tags=["meeting_records"]
)
app.include_router(
    operation_logs_api.router,
    prefix="/api/v1",
    tags=["operation_logs"]
)
app.include_router(
    branding_api.router,
    prefix="/api/v1",
    tags=["branding"]
)


@app.get("/")
async def root() -> dict[str, str]:
    """健康检查接口"""
    return {
        "message": "Feishu Project Manager API",
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/api/v1/health")
async def health_check() -> dict[str, str]:
    """API健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
