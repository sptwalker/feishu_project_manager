from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """健康检查接口"""
    return {
        "message": "Feishu Project Manager API",
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/api/v1/health")
async def health_check():
    """API健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
