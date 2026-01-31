"""
ProFlow - Project Management SaaS Platform
Main application entry point with modular architecture
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from pathlib import Path

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.config import settings
from core.database import get_database
from core.rate_limiter import RateLimitMiddleware
from core.request_logger import RequestLoggingMiddleware, get_request_metrics, reset_request_metrics

# Import routers
from routers import (
    auth_router,
    organization_router,
    project_router,
    task_router,
    customer_router,
    notification_router,
    subscription_router,
    audit_router,
    automation_router,
    reports_router,
    comment_router,
    time_router,
    search_router,
    dashboard_router,
    role_router,
    branding_router,
    health_router,
    ssl_router,
    workflow_router,
    document_router,
    budget_router,
    budget_approval_router,
    custom_reports_router,
    metrics_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ProFlow - Project Management SaaS",
    description="Enterprise-grade project management platform",
    version="2.0.0"
)

# Add Request Logging Middleware (first to capture all requests)
app.add_middleware(RequestLoggingMiddleware)

# Add Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware)

# CORS configuration - use environment variable or allow all
if settings.CORS_ORIGINS and settings.CORS_ORIGINS != "*":
    cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
else:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router
from fastapi import APIRouter
api_router = APIRouter(prefix="/api")

# Register routers
api_router.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(organization_router.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(project_router.router, prefix="/projects", tags=["Projects"])
api_router.include_router(task_router.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(customer_router.router, prefix="/customers", tags=["Customers"])
api_router.include_router(notification_router.router, prefix="/notifications", tags=["Notifications"])
# api_router.include_router(subscription_router.router, prefix="/subscriptions", tags=["Subscriptions"])  # Disabled
api_router.include_router(audit_router.router, prefix="/audit", tags=["Audit Logs"])
api_router.include_router(automation_router.router, prefix="/automations", tags=["Automations"])
api_router.include_router(reports_router.router, prefix="/reports", tags=["Reports"])
api_router.include_router(comment_router.router, prefix="/comments", tags=["Comments"])
api_router.include_router(time_router.router, prefix="/time-entries", tags=["Time Tracking"])
api_router.include_router(search_router.router, prefix="/search", tags=["Search"])
api_router.include_router(dashboard_router.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(role_router.router, tags=["Roles"])
api_router.include_router(branding_router.router, tags=["Branding"])
api_router.include_router(health_router.router, prefix="/health", tags=["Health & Monitoring"])
api_router.include_router(ssl_router.router, prefix="/ssl", tags=["SSL Certificates"])
api_router.include_router(workflow_router.router, prefix="/workflows", tags=["Task Workflows"])
api_router.include_router(document_router.router, prefix="/documents", tags=["Documents"])
api_router.include_router(budget_router.router, prefix="/budgets", tags=["Budgets"])
api_router.include_router(budget_approval_router.router, prefix="/budget-approvals", tags=["Budget Approvals"])
api_router.include_router(custom_reports_router.router, prefix="/custom-reports", tags=["Custom Reports"])
api_router.include_router(metrics_router.router, prefix="/metrics", tags=["API Metrics"])

app.include_router(api_router)

# Health check endpoints - both /health and /api/health for compatibility
@app.get("/health")
async def root_health_check():
    """Root health check endpoint for Kubernetes"""
    from datetime import datetime, timezone
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0"
    }

@app.get("/api/health")
async def api_health_check():
    """API health check endpoint"""
    from datetime import datetime, timezone
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting ProFlow API...")
    
    # Subscription module disabled - skip plan initialization
    # from services.subscription_service import subscription_service
    # await subscription_service.initialize_plans()
    
    logger.info("ProFlow API started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    from core.database import close_connection
    await close_connection()
    logger.info("ProFlow API shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
