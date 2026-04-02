"""统一的 API 响应格式类."""

import json
from dataclasses import dataclass
from typing import Optional, Any, Dict


@dataclass
class ApiResponse:
    """统一的 API 响应格式类"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        response: Dict[str, Any] = {"success": self.success}
        if self.data is not None:
            response["data"] = self.data
        if self.error is not None:
            response["error"] = self.error
        if self.message is not None:
            response["message"] = self.message
        return response

    def to_json(self, compact: bool = True) -> str:
        """转换为 JSON 字符串.

        Args:
            compact: 是否使用紧凑格式（无缩进），默认 True
        """
        if compact:
            return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApiResponse":
        """从字典反序列化创建 ApiResponse."""
        return cls(
            success=data.get("success", False),
            data=data.get("data"),
            message=data.get("message"),
            error=data.get("error")
        )

    @staticmethod
    def success_resp(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        """构建成功响应."""
        return {"success": True, "data": data, "message": message}

    @staticmethod
    def error_resp(error: str) -> Dict[str, Any]:
        """构建错误响应."""
        return {"success": False, "error": error}
