from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import get_settings
from backend.api.v1 import auth, projects, tasks, risks, feishu_webhook, bitable

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
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
