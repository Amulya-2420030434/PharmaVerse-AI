from typing import Any

from fastapi import status


VALIDATION_ERROR = "VALIDATION_ERROR"
AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
FORBIDDEN = "FORBIDDEN"
RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
INVALID_STATE = "INVALID_STATE"
INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
BAD_GATEWAY = "BAD_GATEWAY"
SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


def error_code_for_status(status_code: int) -> str:
    return {
        status.HTTP_400_BAD_REQUEST: INVALID_STATE,
        status.HTTP_401_UNAUTHORIZED: AUTHENTICATION_REQUIRED,
        status.HTTP_403_FORBIDDEN: FORBIDDEN,
        status.HTTP_404_NOT_FOUND: RESOURCE_NOT_FOUND,
        status.HTTP_405_METHOD_NOT_ALLOWED: METHOD_NOT_ALLOWED,
        status.HTTP_409_CONFLICT: RESOURCE_ALREADY_EXISTS,
        422: VALIDATION_ERROR,
        status.HTTP_502_BAD_GATEWAY: BAD_GATEWAY,
        status.HTTP_503_SERVICE_UNAVAILABLE: SERVICE_UNAVAILABLE,
    }.get(status_code, INTERNAL_SERVER_ERROR)


def error_response(
    code: str,
    message: str,
    details: Any | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if details is not None:
        error["details"] = details

    return {
        "success": False,
        "error": error,
    }


def success_response(data: Any, message: str) -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "message": message,
    }
