"""Business API HTTP 服务入口.

提供业务逻辑层的 HTTP API 接口。
端口: 8002
"""

import logging
import os
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 设置存储目录
storage_dir = os.environ.get("MCP_STORAGE_DIR", os.path.join(os.path.expanduser("~"), ".project_memory_ai"))

# ===================
# 日志配置（支持滚动删除）
# ===================
# 从环境变量读取配置，使用默认值
log_level = os.getenv("BUSINESS_LOG_LEVEL", "INFO")
log_dir = os.getenv("LOG_DIR", "/app/logs")
max_bytes = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 默认 10MB
backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))  # 默认保留 5 个文件

from common.logging_config import setup_logging
setup_logging(
    service_name="business",
    log_level=log_level,
    log_dir=log_dir,
    max_bytes=max_bytes,
    backup_count=backup_count,
)
logger = logging.getLogger(__name__)

# 导入 business 层服务
from business.storage import Storage
from business.project_service import ProjectService
from business.tag_service import TagService
from business.stats_service import StatsService

# 初始化 business 层服务
_storage = Storage(storage_dir=storage_dir)
_project_service = ProjectService(_storage)
_tag_service = TagService(_storage)
_stats_service = StatsService(_storage)

# 创建 FastAPI 应用
app = FastAPI(
    title="Business API",
    description="业务逻辑 HTTP 服务",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================
# Health Check
# ===================

@app.get("/health")
async def health_check():
    """健康检查."""
    return {"status": "healthy", "service": "business-api"}


# ===================
# 注册路由
# ===================

from business.api import (
    projects_router, init_projects_services,
    tags_router, init_tags_services,
    stats_router, init_stats_services,
    groups_router, init_groups_services,
)

# 初始化各路由的服务
init_projects_services(_storage, _project_service, _tag_service)
init_tags_services(_tag_service)
init_stats_services(_storage, _stats_service)
init_groups_services(_storage)

# 注册路由
app.include_router(projects_router)
app.include_router(tags_router)
app.include_router(stats_router)
app.include_router(groups_router)


# ===================
# Main Entry Point
# ===================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("BUSINESS_PORT", 8002))
    logger.info(f"启动 Business API 服务...")
    logger.info(f"监听地址: 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
