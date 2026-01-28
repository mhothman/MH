"""SSL Certificate Management Router

Provides endpoints for SSL certificate automation:
- Request new SSL certificates
- Check certificate status
- Manage auto-renewal
- Generate nginx configuration
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, get_user_org_membership
from core.permissions import Permission, has_permission
from services.ssl_service import ssl_service
from services.audit_service import audit_service

logger = logging.getLogger(__name__)
router = APIRouter()


class SSLRequestModel(BaseModel):
    """Request model for SSL certificate"""
    domain: str
    email: Optional[str] = None


class SSLStatusResponse(BaseModel):
    """Response model for SSL status"""
    domain: str
    status: str
    ssl_enabled: bool
    is_valid: Optional[bool] = None
    days_remaining: Optional[int] = None
    needs_renewal: Optional[bool] = None
    issued_at: Optional[str] = None
    valid_until: Optional[str] = None
    issuer: Optional[str] = None
    auto_renew: Optional[bool] = None


@router.post("/org/{org_id}/request")
async def request_ssl_certificate(org_id: str, data: SSLRequestModel, request: Request):
    """
    Request an SSL certificate for a custom domain
    
    Requires: SETTINGS_EDIT permission
    
    Process:
    1. Validates domain ownership via DNS or HTTP challenge
    2. Requests certificate from Let's Encrypt
    3. Configures nginx for SSL
    4. Enables auto-renewal
    """
    db = get_database()
    user = await require_auth(request)
    
    # Check permissions
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.SETTINGS_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot manage SSL certificates")
    
    # Verify domain is configured for this org
    org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if org.get("custom_domain") != data.domain:
        raise HTTPException(
            status_code=400, 
            detail="Domain must be configured as custom domain before requesting SSL"
        )
    
    # Check domain verification status
    if not org.get("domain_verified", False):
        raise HTTPException(
            status_code=400,
            detail="Domain must be verified before requesting SSL certificate"
        )
    
    # Request certificate
    result = await ssl_service.request_certificate(
        domain=data.domain,
        org_id=org_id,
        email=data.email or user.get("email")
    )
    
    # Audit log
    await audit_service.log(
        user["user_id"], 
        org_id, 
        "ssl_certificate_request", 
        "organization", 
        org_id,
        {"domain": data.domain, "status": result.get("status")}
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "SSL certificate request failed"))
    
    return result


@router.get("/org/{org_id}/status")
async def get_ssl_status(org_id: str, request: Request):
    """
    Get SSL certificate status for organization's custom domain
    
    Returns:
    - Certificate status (active, pending, expired, not_configured)
    - Expiration info
    - Renewal status
    """
    db = get_database()
    user = await require_auth(request)
    
    # Check access
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get org domain
    org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    domain = org.get("custom_domain")
    if not domain:
        return {
            "domain": None,
            "status": "no_custom_domain",
            "ssl_enabled": False,
            "message": "No custom domain configured"
        }
    
    status = await ssl_service.get_certificate_status(domain)
    return status


@router.post("/org/{org_id}/renew")
async def renew_ssl_certificate(org_id: str, request: Request):
    """
    Manually trigger SSL certificate renewal
    
    Useful when:
    - Certificate is expiring soon
    - Auto-renewal failed
    - After domain changes
    """
    db = get_database()
    user = await require_auth(request)
    
    # Check permissions
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.SETTINGS_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get org domain
    org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0})
    if not org or not org.get("custom_domain"):
        raise HTTPException(status_code=400, detail="No custom domain configured")
    
    result = await ssl_service.request_certificate(
        domain=org["custom_domain"],
        org_id=org_id,
        email=user.get("email")
    )
    
    await audit_service.log(
        user["user_id"],
        org_id,
        "ssl_certificate_renewal",
        "organization",
        org_id,
        {"domain": org["custom_domain"], "status": result.get("status")}
    )
    
    return result


@router.delete("/org/{org_id}/revoke")
async def revoke_ssl_certificate(org_id: str, request: Request):
    """
    Revoke SSL certificate for custom domain
    
    This will:
    - Revoke the certificate
    - Disable HTTPS for the domain
    - Stop auto-renewal
    """
    db = get_database()
    user = await require_auth(request)
    
    # Check permissions
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.SETTINGS_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get org domain
    org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0})
    if not org or not org.get("custom_domain"):
        raise HTTPException(status_code=400, detail="No custom domain configured")
    
    result = await ssl_service.revoke_certificate(org["custom_domain"], org_id)
    
    await audit_service.log(
        user["user_id"],
        org_id,
        "ssl_certificate_revoked",
        "organization",
        org_id,
        {"domain": org["custom_domain"]}
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/org/{org_id}/nginx-config")
async def get_nginx_config(org_id: str, request: Request):
    """
    Generate nginx SSL configuration for custom domain
    
    Returns the nginx config snippet that should be added
    to enable SSL for the domain.
    """
    db = get_database()
    user = await require_auth(request)
    
    # Check permissions (admin only)
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if membership["role"] not in ["super_admin", "org_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get org domain
    org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0})
    if not org or not org.get("custom_domain"):
        raise HTTPException(status_code=400, detail="No custom domain configured")
    
    config = await ssl_service.generate_nginx_config(org["custom_domain"])
    
    return {
        "domain": org["custom_domain"],
        "nginx_config": config
    }


@router.post("/org/{org_id}/toggle-auto-renew")
async def toggle_auto_renew(org_id: str, enabled: bool, request: Request):
    """Toggle auto-renewal for SSL certificate"""
    db = get_database()
    user = await require_auth(request)
    
    # Check permissions
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.SETTINGS_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get org domain
    org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0})
    if not org or not org.get("custom_domain"):
        raise HTTPException(status_code=400, detail="No custom domain configured")
    
    # Update auto-renew setting
    await db.ssl_certificates.update_one(
        {"domain": org["custom_domain"]},
        {"$set": {"auto_renew": enabled}}
    )
    
    return {
        "success": True,
        "auto_renew": enabled,
        "message": f"Auto-renewal {'enabled' if enabled else 'disabled'}"
    }


# Admin endpoints for system-wide certificate management

@router.get("/admin/all-certificates")
async def get_all_certificates(request: Request):
    """
    Get all SSL certificates (Super Admin only)
    
    Used for monitoring and managing all certificates across the system
    """
    user = await require_auth(request)
    
    # Check super admin
    db = get_database()
    user_data = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not user_data or user_data.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    certificates = await ssl_service.get_all_certificates()
    return certificates


@router.post("/admin/renew-expiring")
async def renew_expiring_certificates(request: Request):
    """
    Renew all certificates expiring soon (Super Admin only)
    
    This is typically run as a scheduled task but can be triggered manually
    """
    user = await require_auth(request)
    
    # Check super admin
    db = get_database()
    user_data = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not user_data or user_data.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    results = await ssl_service.renew_certificates()
    
    logger.info(f"Certificate renewal job completed: {results}")
    
    return results
