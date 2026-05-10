"""统一请求结果处理工具."""

from typing import Any, Optional, Dict

from fastapi import HTTPException

from src.models.response import ApiResponse


async def handle_result(
    result: ApiResponse[Any],
    message: Optional[str] = None,
    error_status: int = 400,
) -> Dict[str, Any]:
    """统一处理客户端返回结果.

    Args:
        result: BusinessApiClient 返回的 ApiResponse 对象
        message: 成功时的自定义消息（覆盖默认消息）
        error_status: 失败时的 HTTP 状态码

    Returns:
        dict: 成功时返回序列化后的字典（response_model 仍能正确生成 OpenAPI）

    Raises:
        HTTPException: 失败时抛出 HTTP 异常
    """
    if result.success:
        if message:
            result = result.model_copy(update={"message": message})
        return result.model_dump()
    raise HTTPException(status_code=error_status, detail=result.error)
