"""全局实例模块.

提供 memory 和 call_stats 全局实例，供其他模块使用。
"""

import os
from pathlib import Path

from features.project import ProjectMemory
from features.stats import CallStats

storage_dir = os.environ.get("MCP_STORAGE_DIR", str(Path.home() / ".project_memory_ai"))
memory = ProjectMemory(storage_dir=storage_dir)
call_stats = CallStats(storage_dir=storage_dir)
