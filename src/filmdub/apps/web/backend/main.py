"""
Web Backend 主入口

影视 AI 配音平台的 Web UI 后端服务
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from filmdub.core.config import settings
from filmdub.core.orchestrator_db import Base
from filmdub.apps.web.backend.api import health, auth, projects, jobs, uploads, characters, system
from filmdub.apps.web.backend.websocket import events


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🚀 Web Backend starting up...")
    yield
    # 关闭时
    print("👋 Web Backend shutting down...")


# 创建 FastAPI 应用
app = FastAPI(
    title="AI-FanYi Web Backend",
    description="影视 AI 配音平台 Web UI 后端 API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(uploads.router, prefix="/api/v1/uploads", tags=["Uploads"])
app.include_router(characters.router, prefix="/api/v1/characters", tags=["Characters"])
app.include_router(system.router, prefix="/api/v1/system", tags=["System"])

# 注册 WebSocket
app.include_router(events.router, prefix="/api/v1/ws", tags=["WebSocket"])


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "AI-FanYi Web Backend",
        "version": "1.0.0",
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "filmdub.apps.web.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
