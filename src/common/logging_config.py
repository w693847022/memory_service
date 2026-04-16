"""日志配置模块 - 支持滚动删除，支持多服务."""

import logging
import logging.handlers
import os
import sys
from pathlib import Path


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    log_dir: str = "/app/logs",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
):
    """配置日志滚动删除.

    Args:
        service_name: 服务名称 (用于创建子目录和日志文件名)
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 日志根目录
        max_bytes: 单个日志文件最大大小（字节）
        backup_count: 保留的旧日志文件数量

    Returns:
        Path: 日志文件目录路径，如果文件日志未启用则返回 None
    """
    # 日志格式
    log_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台处理器（始终启用）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.addHandler(console_handler)

    # 尝试添加文件处理器（可能因权限失败）
    service_log_dir = Path(log_dir) / service_name
    file_handler_added = False

    try:
        # 创建服务日志子目录
        service_log_dir.mkdir(parents=True, exist_ok=True)
        log_file = service_log_dir / f"{service_name}.log"

        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        file_handler.setFormatter(log_format)
        root_logger.addHandler(file_handler)
        file_handler_added = True
    except (PermissionError, OSError) as e:
        root_logger.warning(f"无法创建文件日志处理器: {e}，仅使用控制台日志")

    # 配置 Uvicorn 日志（仅 FastAPI 服务需要）
    if service_name == "fastapi":
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    return service_log_dir if file_handler_added else None


def get_request_id(record: logging.LogRecord) -> str:
    """从日志记录中提取 request_id."""
    request_id = getattr(record, 'request_id', None)
    if request_id:
        return f"[{request_id}] "
    return ""
