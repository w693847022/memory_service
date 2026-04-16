"""HTTP 客户端连接池配置.

通过环境变量配置连接池参数，支持 HTTP/2 可选启用。
"""

import httpx

from src.models.config import ConnectionPoolConfig
