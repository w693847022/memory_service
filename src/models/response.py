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
