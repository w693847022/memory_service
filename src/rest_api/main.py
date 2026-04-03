"""FastAPI REST API 层 - 为前端提供 HTTP 接口."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .mcp_client import get_mcp_client
from .middleware import RequestTrackerMiddleware
from common.logging_config import setup_logging

# ===================
# 日志配置（支持滚动删除）
# ===================
# 从环境变量读取配置，使用默认值
log_level = os.getenv("LOG_LEVEL", "INFO")
log_dir = os.getenv("LOG_DIR", "/app/logs")
max_bytes = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 默认 10MB
backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))  # 默认保留 5 个文件

setup_logging(
    service_name="fastapi",
    log_level=log_level,
    log_dir=log_dir,
    max_bytes=max_bytes,
    backup_count=backup_count,
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
# 速率限制配置
# ===================
# 从环境变量读取速率限制配置，默认 200/分钟
default_rate_limit = os.getenv("RATE_LIMIT_DEFAULT", "200/minute")
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[default_rate_limit],
    storage_uri="memory://",  # 内存存储（单实例）
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ===================
# 请求追踪中间件
# ===================
app.add_middleware(RequestTrackerMiddleware)


# ===================
# 统一响应格式
# ===================

from common.response import ApiResponse


# ===================
# 异常处理
# ===================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error_resp(f"Internal server error: {str(exc)}")
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """参数验证错误处理."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ApiResponse.error_resp(str(exc))
    )


# ===================
# 健康检查
# ===================

@app.get("/health", tags=["Health"])
@limiter.limit(os.getenv("RATE_LIMIT_HEALTH", "60/minute"))
async def health_check(request: Request):
    """健康检查端点."""
    return ApiResponse.success_resp(data={"status": "healthy"})


@app.get("/", tags=["Root"])
@limiter.limit("30/minute")
async def root(request: Request):
    """根路径."""
    return ApiResponse.success_resp(data={
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
