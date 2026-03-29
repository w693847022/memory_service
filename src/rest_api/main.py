"""FastAPI REST API 层 - 为前端提供 HTTP 接口."""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .mcp_client import get_mcp_client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===================
# 生命周期管理
# ===================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理."""
    logger.info("FastAPI 应用启动")
    yield
    logger.info("FastAPI 应用关闭")


# ===================
# 应用初始化
# ===================

app = FastAPI(
    title="Project Memory REST API",
    description="FastAPI REST API 层，为前端提供项目记忆管理 HTTP 接口",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================
# 统一响应格式
# ===================

class ApiResponse:
    """统一 API 响应格式."""

    @staticmethod
    def success(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        return {
            "success": True,
            "data": data,
            "message": message
        }

    @staticmethod
    def error(error: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": error
            }
        )


# ===================
# 异常处理
# ===================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return ApiResponse.error(
        error=f"Internal server error: {str(exc)}",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """参数验证错误处理."""
    logger.warning(f"Validation error: {exc}")
    return ApiResponse.error(
        error=str(exc),
        status_code=status.HTTP_400_BAD_REQUEST
    )


# ===================
# 请求日志中间件
# ===================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求."""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - {response.status_code}")
    return response


# ===================
# 健康检查
# ===================

@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查端点."""
    return ApiResponse.success(data={"status": "healthy"})


@app.get("/", tags=["Root"])
async def root():
    """根路径."""
    return ApiResponse.success(data={
        "name": "Project Memory REST API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    })


# ===================
# 注册路由
# ===================

from .routers import (
    projects,
    groups,
    tags,
    stats,
)

app.include_router(projects.router, prefix="/api", tags=["Projects"])
app.include_router(groups.router, prefix="/api", tags=["Groups"])
app.include_router(tags.router, prefix="/api", tags=["Tags"])
app.include_router(stats.router, prefix="/api", tags=["Stats"])
