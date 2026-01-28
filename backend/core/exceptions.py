"""Custom exceptions for the application"""
from fastapi import HTTPException
from typing import Optional, Dict, Any

class AppException(HTTPException):
    """Base application exception"""
    def __init__(
        self,
        status_code: int = 500,
        detail: str = "An error occurred",
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)

class AuthenticationError(AppException):
    """Authentication failed"""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status_code=401, detail=detail)

class AuthorizationError(AppException):
    """Authorization failed - insufficient permissions"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=403, detail=detail)

class NotFoundError(AppException):
    """Resource not found"""
    def __init__(self, resource: str = "Resource", detail: Optional[str] = None):
        message = detail or f"{resource} not found"
        super().__init__(status_code=404, detail=message)

class ValidationError(AppException):
    """Validation error"""
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(status_code=400, detail=detail)

class ConflictError(AppException):
    """Resource conflict"""
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=409, detail=detail)

class RateLimitError(AppException):
    """Rate limit exceeded"""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(status_code=429, detail=detail)
