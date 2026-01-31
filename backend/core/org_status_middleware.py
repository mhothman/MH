"""Organization Status Middleware - Block suspended organizations"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

from core.database import get_database

logger = logging.getLogger(__name__)


class OrganizationStatusMiddleware(BaseHTTPMiddleware):
    """Middleware to check if organization is suspended"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip for tenant-admin routes
        if request.url.path.startswith("/api/tenant-admin"):
            return await call_next(request)
        
        # Skip for auth routes
        if request.url.path.startswith("/api/auth"):
            return await call_next(request)
        
        # Skip for health checks
        if request.url.path.startswith("/health") or request.url.path.startswith("/api/health"):
            return await call_next(request)
        
        # Check if org_id is in query params
        org_id = request.query_params.get("org_id")
        
        if org_id:
            db = get_database()
            org = await db.organizations.find_one(
                {"org_id": org_id},
                {"_id": 0, "status": 1}
            )
            
            if org and org.get("status") == "suspended":
                return Response(
                    content='{"detail":"Organization is suspended. Contact tenant administrator."}',
                    status_code=403,
                    media_type="application/json"
                )
        
        # Continue with request
        response = await call_next(request)
        return response
