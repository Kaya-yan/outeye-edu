"""
错误处理工具模块
"""

from fastapi import HTTPException, status
from loguru import logger


def handle_api_error(e: Exception, operation: str = "operation") -> HTTPException:
    """
    处理API错误，返回安全的错误响应

    Args:
        e: 捕获的异常
        operation: 操作描述

    Returns:
        HTTPException: 不泄露内部信息的错误响应
    """
    error_type = type(e).__name__
    logger.error(f"{operation} failed: {error_type}: {e}")

    # 根据异常类型返回适当的错误信息
    if isinstance(e, ValueError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    elif isinstance(e, FileNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    elif isinstance(e, PermissionError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    elif isinstance(e, TimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out"
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
