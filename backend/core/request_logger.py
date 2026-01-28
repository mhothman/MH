"""Request logging and monitoring middleware"""
import time
import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Optional, Callable
from collections import defaultdict
from dataclasses import dataclass, field
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Container for request metrics"""
    total_requests: int = 0
    total_errors: int = 0
    total_response_time_ms: float = 0
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    endpoint_stats: Dict[str, Dict] = field(default_factory=lambda: defaultdict(lambda: {
        "count": 0,
        "errors": 0,
        "total_time_ms": 0,
        "min_time_ms": float('inf'),
        "max_time_ms": 0
    }))
    slow_requests: list = field(default_factory=list)
    error_requests: list = field(default_factory=list)
    
    def add_request(self, endpoint: str, status_code: int, duration_ms: float, 
                    request_id: str, method: str, error_detail: Optional[str] = None):
        """Record a request"""
        self.total_requests += 1
        self.total_response_time_ms += duration_ms
        self.status_codes[status_code] += 1
        
        # Update endpoint stats
        stats = self.endpoint_stats[endpoint]
        stats["count"] += 1
        stats["total_time_ms"] += duration_ms
        stats["min_time_ms"] = min(stats["min_time_ms"], duration_ms)
        stats["max_time_ms"] = max(stats["max_time_ms"], duration_ms)
        
        # Track errors
        if status_code >= 400:
            self.total_errors += 1
            stats["errors"] += 1
            
            # Keep last 100 errors
            if len(self.error_requests) >= 100:
                self.error_requests.pop(0)
            self.error_requests.append({
                "request_id": request_id,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "error": error_detail,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        # Track slow requests (> 1000ms)
        if duration_ms > 1000:
            if len(self.slow_requests) >= 50:
                self.slow_requests.pop(0)
            self.slow_requests.append({
                "request_id": request_id,
                "endpoint": endpoint,
                "method": method,
                "duration_ms": round(duration_ms, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    def get_summary(self) -> Dict:
        """Get metrics summary"""
        avg_response_time = (
            self.total_response_time_ms / self.total_requests 
            if self.total_requests > 0 else 0
        )
        error_rate = (
            self.total_errors / self.total_requests * 100 
            if self.total_requests > 0 else 0
        )
        
        # Get top slowest endpoints
        slowest_endpoints = sorted(
            [
                {
                    "endpoint": ep,
                    "avg_time_ms": round(stats["total_time_ms"] / stats["count"], 2) if stats["count"] > 0 else 0,
                    "max_time_ms": round(stats["max_time_ms"], 2),
                    "count": stats["count"]
                }
                for ep, stats in self.endpoint_stats.items()
                if stats["count"] > 0
            ],
            key=lambda x: x["avg_time_ms"],
            reverse=True
        )[:10]
        
        # Get endpoints with most errors
        error_endpoints = sorted(
            [
                {
                    "endpoint": ep,
                    "errors": stats["errors"],
                    "error_rate": round(stats["errors"] / stats["count"] * 100, 2) if stats["count"] > 0 else 0,
                    "count": stats["count"]
                }
                for ep, stats in self.endpoint_stats.items()
                if stats["errors"] > 0
            ],
            key=lambda x: x["errors"],
            reverse=True
        )[:10]
        
        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate_percent": round(error_rate, 2),
            "avg_response_time_ms": round(avg_response_time, 2),
            "status_code_distribution": dict(self.status_codes),
            "slowest_endpoints": slowest_endpoints,
            "error_endpoints": error_endpoints,
            "recent_slow_requests": self.slow_requests[-10:],
            "recent_errors": self.error_requests[-10:]
        }
    
    def reset(self):
        """Reset all metrics"""
        self.total_requests = 0
        self.total_errors = 0
        self.total_response_time_ms = 0
        self.status_codes.clear()
        self.endpoint_stats.clear()
        self.slow_requests.clear()
        self.error_requests.clear()


# Global metrics instance
request_metrics = RequestMetrics()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging requests and collecting metrics.
    
    Features:
    - Request ID generation and tracking
    - Response time measurement
    - Error logging with details
    - Slow request detection
    - Metrics collection for monitoring
    """
    
    # Paths to exclude from detailed logging
    EXCLUDED_PATHS = {
        "/health",
        "/api/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    }
    
    # Log level thresholds (in ms)
    SLOW_REQUEST_THRESHOLD = 1000
    VERY_SLOW_REQUEST_THRESHOLD = 5000
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Add request ID to state for use in handlers
        request.state.request_id = request_id
        
        # Get request details
        method = request.method
        path = request.url.path
        query = str(request.query_params) if request.query_params else ""
        client_ip = self._get_client_ip(request)
        
        # Skip detailed logging for excluded paths
        if path in self.EXCLUDED_PATHS:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        
        # Start timing
        start_time = time.perf_counter()
        
        # Log request start
        logger.info(
            f"[{request_id}] --> {method} {path}"
            f"{' ?' + query if query else ''}"
            f" from {client_ip}"
        )
        
        # Process request
        error_detail = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Try to get error detail for 4xx/5xx responses
            if status_code >= 400:
                # For error responses, we can't easily read the body
                # without consuming it, so we'll just note the status
                error_detail = f"HTTP {status_code}"
                
        except Exception as e:
            # Log unhandled exception
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] <-- {method} {path} "
                f"EXCEPTION after {duration_ms:.2f}ms: {str(e)}"
            )
            
            # Record metrics for exception
            request_metrics.add_request(
                endpoint=path,
                status_code=500,
                duration_ms=duration_ms,
                request_id=request_id,
                method=method,
                error_detail=str(e)
            )
            raise
        
        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # Determine log level based on status and duration
        if status_code >= 500:
            log_func = logger.error
            log_prefix = "ERROR"
        elif status_code >= 400:
            log_func = logger.warning
            log_prefix = "WARN"
        elif duration_ms > self.VERY_SLOW_REQUEST_THRESHOLD:
            log_func = logger.warning
            log_prefix = "VERY SLOW"
        elif duration_ms > self.SLOW_REQUEST_THRESHOLD:
            log_func = logger.warning
            log_prefix = "SLOW"
        else:
            log_func = logger.info
            log_prefix = "OK"
        
        # Log response
        log_func(
            f"[{request_id}] <-- {method} {path} "
            f"{status_code} {log_prefix} "
            f"({duration_ms:.2f}ms)"
        )
        
        # Record metrics
        request_metrics.add_request(
            endpoint=path,
            status_code=status_code,
            duration_ms=duration_ms,
            request_id=request_id,
            method=method,
            error_detail=error_detail
        )
        
        # Add headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, considering proxies"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


def get_request_metrics() -> Dict:
    """Get current request metrics summary"""
    return request_metrics.get_summary()


def reset_request_metrics():
    """Reset request metrics (useful for testing or periodic resets)"""
    request_metrics.reset()


# Utility decorator for timing specific functions
def log_execution_time(name: Optional[str] = None):
    """Decorator to log function execution time"""
    def decorator(func: Callable):
        func_name = name or func.__name__
        
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                logger.debug(f"[TIMING] {func_name}: {duration:.2f}ms")
                return result
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                logger.error(f"[TIMING] {func_name}: {duration:.2f}ms (FAILED: {e})")
                raise
        
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                logger.debug(f"[TIMING] {func_name}: {duration:.2f}ms")
                return result
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                logger.error(f"[TIMING] {func_name}: {duration:.2f}ms (FAILED: {e})")
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
