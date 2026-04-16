"""
Pydantic models for API responses.

These models define the standard response format for all API endpoints.
"""

from typing import Any, Dict, Optional, TypeVar, Generic
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    Unified API response format.

    Provides a consistent structure for all API responses, including
    success status, data payload, error messages, and informational messages.

    Type Parameters:
        T: The type of data contained in the response (use Any for untyped responses)
    """

    success: bool = Field(
        ...,
        description="Whether the operation was successful"
    )
    data: Optional[T] = Field(
        default=None,
        description="Response data payload (present on successful operations)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message (present on failed operations)"
    )
    message: Optional[str] = Field(
        default=None,
        description="Informational message about the operation"
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the response to a dictionary.

        Returns:
            Dictionary representation of the response with only populated fields
        """
        result: Dict[str, Any] = {"success": self.success}
        if self.data is not None:
            result["data"] = self.data
        if self.error is not None:
            result["error"] = self.error
        if self.message is not None:
            result["message"] = self.message
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApiResponse[T]":
        """
        Create an ApiResponse from a dictionary.

        Args:
            data: Dictionary containing response data

        Returns:
            ApiResponse instance created from the dictionary
        """
        return cls(
            success=data.get("success", False),
            data=data.get("data"),
            message=data.get("message"),
            error=data.get("error"),
        )

    @classmethod
    def success_response(
        cls,
        data: Optional[T] = None,
        message: str = "Success"
    ) -> "ApiResponse[T]":
        """
        Create a successful response.

        Args:
            data: Response data payload
            message: Optional informational message

        Returns:
            ApiResponse with success=True and provided data/message
        """
        return cls(success=True, data=data, message=message)

    @classmethod
    def error_response(
        cls,
        error: str,
        data: Optional[T] = None
    ) -> "ApiResponse[T]":
        """
        Create an error response.

        Args:
            error: Error message describing what went wrong
            data: Optional data to include with the error

        Returns:
            ApiResponse with success=False and error message
        """
        return cls(success=False, error=error, data=data)

    model_config = {
        "populate_by_name": True,
        "json_encoders": {
            # Add custom JSON encoders if needed
        },
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "data": {"id": "123", "name": "example"},
                    "error": None,
                    "message": "Operation completed successfully"
                },
                {
                    "success": False,
                    "data": None,
                    "error": "Resource not found",
                    "message": None
                }
            ]
        }
    }


class ResponseBuilder:
    """响应构建器工具类

    提供便捷的方法来构建标准化的API响应，支持链式调用。
    """

    def __init__(self):
        """初始化响应构建器"""
        self._data: Optional[Any] = None
        self._error: Optional[str] = None
        self._message: Optional[str] = None
        self._success: bool = True

    def with_data(self, data: Any) -> "ResponseBuilder":
        """设置响应数据

        Args:
            data: 响应数据载荷

        Returns:
            ResponseBuilder: 返回自身以支持链式调用
        """
        self._data = data
        return self

    def with_error(self, error: str) -> "ResponseBuilder":
        """设置错误消息

        Args:
            error: 错误消息描述

        Returns:
            ResponseBuilder: 返回自身以支持链式调用
        """
        self._error = error
        self._success = False
        return self

    def with_message(self, message: str) -> "ResponseBuilder":
        """设置信息消息

        Args:
            message: 信息消息

        Returns:
            ResponseBuilder: 返回自身以支持链式调用
        """
        self._message = message
        return self

    def with_success(self, success: bool = True) -> "ResponseBuilder":
        """设置成功状态

        Args:
            success: 操作是否成功

        Returns:
            ResponseBuilder: 返回自身以支持链式调用
        """
        self._success = success
        return self

    def build(self) -> ApiResponse[Any]:
        """构建最终的ApiResponse对象

        Returns:
            ApiResponse: 构建好的API响应对象
        """
        return ApiResponse(
            success=self._success,
            data=self._data,
            error=self._error,
            message=self._message
        )

    @classmethod
    def success(cls, data: Any = None, message: Optional[str] = None) -> ApiResponse[Any]:
        """快速构建成功响应

        Args:
            data: 响应数据载荷
            message: 可选的信息消息

        Returns:
            ApiResponse: 成功响应对象
        """
        builder = cls().with_data(data)
        if message is not None:
            builder.with_message(message)
        return builder.build()

    @classmethod
    def error(cls, error: str, data: Any = None) -> ApiResponse[Any]:
        """快速构建错误响应

        Args:
            error: 错误消息描述
            data: 可选的额外数据

        Returns:
            ApiResponse: 错误响应对象
        """
        return cls().with_error(error).with_data(data).build()

    @classmethod
    def message(cls, message: str, data: Any = None) -> ApiResponse[Any]:
        """快速构建仅包含消息的响应

        Args:
            message: 信息消息
            data: 可选的响应数据

        Returns:
            ApiResponse: 响应对象
        """
        return cls().with_message(message).with_data(data).build() if data else cls().with_message(message).build()

    def reset(self) -> "ResponseBuilder":
        """重置构建器状态

        Returns:
            ResponseBuilder: 返回自身以支持链式调用
        """
        self._data = None
        self._error = None
        self._message = None
        self._success = True
        return self
