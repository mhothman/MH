"""Rate limiting middleware for API protection"""
import time
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": retry_after
            }
        )
        self.retry_after = retry_after


class RateLimiter:
    """
    Token bucket rate limiter implementation.
    
    Limits are defined per key (usually IP or user ID) with configurable
    requests per window and window duration.
    """
    
    def __init__(
        self,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        burst_multiplier: float = 1.5
    ):
        """
        Initialize the rate limiter.
        
        Args:
            requests_per_window: Maximum requests allowed per window
            window_seconds: Duration of the rate limit window
            burst_multiplier: Allow temporary burst above limit (default 1.5x)
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.burst_limit = int(requests_per_window * burst_multiplier)
        
        # Storage: key -> (tokens, last_update_time)
        self._buckets: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (float(self.requests_per_window), time.time())
        )
        
        # Track blocked keys for logging
        self._blocked_keys: Dict[str, float] = {}
    
    def _refill_tokens(self, key: str) -> float:
        """Refill tokens based on time elapsed"""
        tokens, last_update = self._buckets[key]
        now = time.time()
        time_passed = now - last_update
        
        # Calculate how many tokens to add
        refill_rate = self.requests_per_window / self.window_seconds
        new_tokens = min(
            float(self.burst_limit),  # Cap at burst limit
            tokens + (time_passed * refill_rate)
        )
        
        self._buckets[key] = (new_tokens, now)
        return new_tokens
    
    def is_allowed(self, key: str, cost: float = 1.0) -> Tuple[bool, float, int]:
        """
        Check if a request is allowed and consume tokens.
        
        Args:
            key: Identifier for rate limiting (IP, user ID, etc.)
            cost: Cost of this request in tokens (default 1.0)
        
        Returns:
            Tuple of (allowed, remaining_tokens, retry_after_seconds)
        """
        tokens = self._refill_tokens(key)
        
        if tokens >= cost:
            # Allow request and consume token
            self._buckets[key] = (tokens - cost, time.time())
            
            # Clear from blocked keys if previously blocked
            if key in self._blocked_keys:
                del self._blocked_keys[key]
            
            return True, tokens - cost, 0
        else:
            # Calculate retry after
            tokens_needed = cost - tokens
            refill_rate = self.requests_per_window / self.window_seconds
            retry_after = int(tokens_needed / refill_rate) + 1
            
            # Track blocked key
            self._blocked_keys[key] = time.time()
            
            return False, tokens, retry_after
    
    def get_headers(self, key: str) -> Dict[str, str]:
        """Get rate limit headers for response"""
        tokens, _ = self._buckets.get(key, (float(self.requests_per_window), time.time()))
        
        return {
            "X-RateLimit-Limit": str(self.requests_per_window),
            "X-RateLimit-Remaining": str(max(0, int(tokens))),
            "X-RateLimit-Reset": str(int(time.time()) + self.window_seconds)
        }
    
    def cleanup_old_entries(self, max_age_seconds: int = 3600):
        """Remove old entries to prevent memory growth"""
        now = time.time()
        keys_to_remove = [
            key for key, (_, last_update) in self._buckets.items()
            if now - last_update > max_age_seconds
        ]
        for key in keys_to_remove:
            del self._buckets[key]


# Global rate limiters with different configurations
rate_limiters = {
    # General API rate limit: 200 requests per minute (increased for testing)
    "default": RateLimiter(requests_per_window=200, window_seconds=60),
    
    # Auth endpoints: moderate limit to prevent brute force
    "auth": RateLimiter(requests_per_window=60, window_seconds=60),
    
    # Write operations: generous limit
    "write": RateLimiter(requests_per_window=120, window_seconds=60),
    
    # Heavy operations (reports, exports): lower limit
    "heavy": RateLimiter(requests_per_window=30, window_seconds=60),
}


def get_rate_limit_key(request: Request) -> str:
    """
    Generate a rate limit key for the request.
    Uses IP address, with consideration for proxies.
    """
    # Check for forwarded headers (behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    
    return f"ip:{client_ip}"


def get_rate_limiter_type(request: Request) -> str:
    """Determine which rate limiter to use based on the endpoint"""
    path = request.url.path.lower()
    method = request.method.upper()
    
    # Auth endpoints
    if "/auth/" in path:
        return "auth"
    
    # Heavy operations
    if "/reports/" in path or "/export" in path or "/dashboard" in path:
        return "heavy"
    
    # Write operations
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return "write"
    
    return "default"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    
    Applies token bucket rate limiting based on client IP.
    Different limits apply to different endpoint types.
    """
    
    # Paths to exclude from rate limiting
    EXCLUDED_PATHS = {
        "/health",
        "/api/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Get rate limit key and limiter type
        key = get_rate_limit_key(request)
        limiter_type = get_rate_limiter_type(request)
        limiter = rate_limiters.get(limiter_type, rate_limiters["default"])
        
        # Check rate limit
        allowed, remaining, retry_after = limiter.is_allowed(key)
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {key} on {request.url.path} "
                f"(type: {limiter_type}, retry_after: {retry_after}s)"
            )
            
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": retry_after
                }
            )
            response.headers["Retry-After"] = str(retry_after)
            response.headers.update(limiter.get_headers(key))
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        for header, value in limiter.get_headers(key).items():
            response.headers[header] = value
        
        return response


# Utility function for manual rate limit checks in routes
async def check_rate_limit(
    request: Request,
    limiter_type: str = "default",
    cost: float = 1.0
) -> None:
    """
    Manually check rate limit within a route handler.
    Raises HTTPException if limit exceeded.
    
    Usage:
        @router.post("/heavy-operation")
        async def heavy_operation(request: Request):
            await check_rate_limit(request, "heavy", cost=5.0)
            # ... rest of handler
    """
    key = get_rate_limit_key(request)
    limiter = rate_limiters.get(limiter_type, rate_limiters["default"])
    
    allowed, remaining, retry_after = limiter.is_allowed(key, cost)
    
    if not allowed:
        raise RateLimitExceeded(retry_after=retry_after)
