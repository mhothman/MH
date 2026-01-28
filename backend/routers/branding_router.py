"""Organization Branding Router - Refactored to use BrandingService"""
import logging
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, get_user_org_membership, require_permission
from models.branding import BrandingUpdate, BrandingResponse, BrandingPublic
from services.branding_service import branding_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/branding", tags=["branding"])


# =============================================
# Metadata Endpoints
# =============================================

@router.get("/fonts")
async def get_preset_fonts():
    """Get list of available preset fonts"""
    from models.branding import PRESET_FONTS
    return {"fonts": PRESET_FONTS}


@router.get("/themes")
async def get_preset_themes():
    """Get list of available preset theme templates"""
    from models.branding import PRESET_THEMES
    return {"themes": PRESET_THEMES}


# =============================================
# Branding CRUD
# =============================================

@router.get("/org/{org_id}", response_model=BrandingResponse)
async def get_branding(org_id: str, request: Request):
    """Get organization branding settings"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    branding = await branding_service.get_branding(org_id)
    return BrandingResponse(**branding)


@router.get("/org/{org_id}/public", response_model=BrandingPublic)
async def get_public_branding(org_id: str, request: Request):
    """Get published branding for display (accessible to all org members)"""
    db = get_database()
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0, "name": 1})
    org_name = org.get("name", "Organization") if org else "Organization"
    
    branding = await branding_service.get_public_branding(org_id, org_name)
    return BrandingPublic(**branding)


@router.put("/org/{org_id}", response_model=BrandingResponse)
async def update_branding(org_id: str, data: BrandingUpdate, request: Request):
    """Update organization branding (draft mode)"""
    user = await require_permission(request, org_id, "settings:edit")
    
    branding = await branding_service.update_branding(
        org_id=org_id,
        user_id=user["user_id"],
        **data.model_dump(exclude_none=True)
    )
    
    return BrandingResponse(**branding)


@router.post("/org/{org_id}/publish", response_model=BrandingResponse)
async def publish_branding(org_id: str, request: Request):
    """Publish branding changes to make them visible to all users"""
    user = await require_permission(request, org_id, "settings:edit")
    
    success, message, branding = await branding_service.publish_branding(org_id, user["user_id"])
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return BrandingResponse(**branding)


@router.post("/org/{org_id}/reset", response_model=BrandingResponse)
async def reset_branding(org_id: str, request: Request):
    """Reset branding to default"""
    user = await require_permission(request, org_id, "settings:edit")
    
    branding = await branding_service.reset_branding(org_id, user["user_id"])
    return BrandingResponse(**branding)


# =============================================
# Logo Management
# =============================================

@router.post("/org/{org_id}/logo")
async def upload_logo(org_id: str, request: Request, file: UploadFile = File(...)):
    """Upload organization logo"""
    user = await require_permission(request, org_id, "settings:edit")
    
    content = await file.read()
    
    success, message, logo_url = await branding_service.upload_logo(
        org_id=org_id,
        user_id=user["user_id"],
        filename=file.filename,
        content=content
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"logo_url": logo_url, "filename": file.filename}


@router.delete("/org/{org_id}/logo")
async def delete_logo(org_id: str, request: Request):
    """Delete organization logo"""
    user = await require_permission(request, org_id, "settings:edit")
    
    success, message = await branding_service.delete_logo(org_id, user["user_id"])
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message}


@router.get("/logo/{filename}")
async def get_logo(filename: str):
    """Serve logo file"""
    filepath = branding_service.get_logo_path(filename)
    
    if not filepath:
        raise HTTPException(status_code=404, detail="Logo not found")
    
    media_type = branding_service.get_media_type(filename)
    return FileResponse(filepath, media_type=media_type)
