#!/usr/bin/env python
"""Business API 服务启动脚本.

独立启动 Business HTTP API 服务（端口 8002）。
"""

import sys
import os
from pathlib import Path

# 添加 src 目录到 Python 路径
# 检测运行环境：Docker 中脚本位于 /app/，本地位于 /path/to/project/scripts/
if Path(__file__).parent.name == "app" or str(Path(__file__).parent) == "/app":
    # Docker 环境
    src_path = Path("/app/src")
    project_root = Path("/app")
else:
    # 本地环境
    project_root = Path(__file__).parent.parent
    src_path = project_root / "src"

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    import uvicorn
    from business.main import app

    port = int(os.environ.get("BUSINESS_PORT", 8002))
    host = os.environ.get("BUSINESS_HOST", "0.0.0.0")

    print(f"启动 Business API 服务...")
    print(f"监听地址: {host}:{port}")
    print(f"健康检查: http://{host}:{port}/health")
    print()

    uvicorn.run(app, host=host, port=port)
