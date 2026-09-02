from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_v1_router
from app.core.config import settings

app = FastAPI(
    title="Deep Research Agent API",
    description="自主型多智能体深度研究与知识整理助手后端服务 (支持 LangGraph 状态机编排与 SSE 实时流式传输)",
    version="0.4.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 允许跨域请求 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 API v1 路由 (/api/v1/...)
app.include_router(api_v1_router, prefix="/api")

# 前端静态资源目录
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    # 挂载静态静态文件与 assets
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/", tags=["Frontend"])
    async def serve_frontend_index():
        """提供前端单页面应用入口"""
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/", tags=["Index"])
    async def index():
        return {
            "status": "ready",
            "message": "Deep Research Agent API Backend is running.",
            "docs": "/docs",
            "health": "/health"
        }

@app.get("/health", tags=["Health"])
async def health_check():
    """服务健康检查接口"""
    return {
        "status": "healthy",
        "service": "Deep Research Agent Backend",
        "version": "0.4.0",
        "llm_model": settings.LLM_MODEL
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常捕获"""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)}
    )
