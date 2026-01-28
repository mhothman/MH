"""Branding Service - Business logic for organization branding"""
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, Any

from core.database import get_database
from services.audit_service import audit_service

logger = logging.getLogger(__name__)

UPLOAD_DIR = "/app/uploads/logos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB

DEFAULT_BRANDING = {
    "logo_url": None,
    "primary_color": "#0f172a",
    "secondary_color": "#3b82f6",
    "accent_color": "#10b981",
    "dark_mode_supported": True,
    "heading_font": "inter",
    "heading_font_url": None,
    "body_font": "inter",
    "body_font_url": None,
    "custom_css": None,
    "published": False
}


class BrandingService:
    """Service for organization branding business logic"""
    
    # =============================================
    # Branding CRUD
    # =============================================
    
    async def get_branding(self, org_id: str) -> Dict:
        """Get organization branding settings"""
        db = get_database()
        
        branding = await db.organization_branding.find_one(
            {"organization_id": org_id},
            {"_id": 0}
        )
        
        if not branding:
            now = datetime.now(timezone.utc).isoformat()
            return {
                "branding_id": f"brand_default_{org_id[:8]}",
                "organization_id": org_id,
                **DEFAULT_BRANDING,
                "created_at": now,
                "updated_at": now
            }
        
        return branding
    
    async def get_public_branding(self, org_id: str, org_name: str) -> Dict:
        """Get published branding for display"""
        db = get_database()
        
        branding = await db.organization_branding.find_one(
            {"organization_id": org_id, "published": True},
            {"_id": 0}
        )
        
        if not branding:
            return {
                "organization_name": org_name,
                **{k: v for k, v in DEFAULT_BRANDING.items() if k != "published"}
            }
        
        return {
            "logo_url": branding.get("logo_url"),
            "primary_color": branding.get("primary_color", DEFAULT_BRANDING["primary_color"]),
            "secondary_color": branding.get("secondary_color", DEFAULT_BRANDING["secondary_color"]),
            "accent_color": branding.get("accent_color", DEFAULT_BRANDING["accent_color"]),
            "dark_mode_supported": branding.get("dark_mode_supported", True),
            "organization_name": org_name,
            "heading_font": branding.get("heading_font", DEFAULT_BRANDING["heading_font"]),
            "heading_font_url": branding.get("heading_font_url"),
            "body_font": branding.get("body_font", DEFAULT_BRANDING["body_font"]),
            "body_font_url": branding.get("body_font_url"),
            "custom_css": branding.get("custom_css")
        }
    
    async def update_branding(
        self,
        org_id: str,
        user_id: str,
        **updates
    ) -> Dict:
        """Update organization branding (draft mode)"""
        db = get_database()
        now = datetime.now(timezone.utc).isoformat()
        
        existing = await db.organization_branding.find_one({"organization_id": org_id})
        
        if existing:
            update_data = {k: v for k, v in updates.items() if v is not None}
            update_data["updated_at"] = now
            
            await db.organization_branding.update_one(
                {"organization_id": org_id},
                {"$set": update_data}
            )
            
            branding = await db.organization_branding.find_one(
                {"organization_id": org_id},
                {"_id": 0}
            )
        else:
            branding_id = f"brand_{uuid.uuid4().hex[:12]}"
            branding = {
                "branding_id": branding_id,
                "organization_id": org_id,
                **DEFAULT_BRANDING,
                **{k: v for k, v in updates.items() if v is not None},
                "created_at": now,
                "updated_at": now
            }
            await db.organization_branding.insert_one(branding)
            branding.pop("_id", None)
        
        await audit_service.log(
            user_id, org_id, "update", "branding",
            branding.get("branding_id", "unknown"),
            {"updated_fields": list(updates.keys())}
        )
        
        logger.info(f"Branding updated for org {org_id} by user {user_id}")
        return branding
    
    async def publish_branding(self, org_id: str, user_id: str) -> Tuple[bool, str, Optional[Dict]]:
        """Publish branding changes"""
        db = get_database()
        now = datetime.now(timezone.utc).isoformat()
        
        branding = await db.organization_branding.find_one({"organization_id": org_id})
        
        if not branding:
            return False, "No branding settings found. Please configure branding first.", None
        
        await db.organization_branding.update_one(
            {"organization_id": org_id},
            {"$set": {"published": True, "updated_at": now}}
        )
        
        branding = await db.organization_branding.find_one(
            {"organization_id": org_id},
            {"_id": 0}
        )
        
        await audit_service.log(
            user_id, org_id, "update", "branding",
            branding["branding_id"],
            {"action": "published"}
        )
        
        logger.info(f"Branding published for org {org_id} by user {user_id}")
        return True, "Branding published", branding
    
    async def reset_branding(self, org_id: str, user_id: str) -> Dict:
        """Reset branding to default"""
        db = get_database()
        now = datetime.now(timezone.utc).isoformat()
        
        existing = await db.organization_branding.find_one({"organization_id": org_id})
        
        if existing:
            old_values = {
                "logo_url": existing.get("logo_url"),
                "primary_color": existing.get("primary_color"),
                "secondary_color": existing.get("secondary_color"),
                "accent_color": existing.get("accent_color")
            }
            
            await db.organization_branding.update_one(
                {"organization_id": org_id},
                {"$set": {**DEFAULT_BRANDING, "updated_at": now}}
            )
            
            await audit_service.log(
                user_id, org_id, "update", "branding",
                existing["branding_id"],
                {"action": "reset", "previous_values": old_values}
            )
        
        branding = await db.organization_branding.find_one(
            {"organization_id": org_id},
            {"_id": 0}
        )
        
        if not branding:
            branding_id = f"brand_{uuid.uuid4().hex[:12]}"
            branding = {
                "branding_id": branding_id,
                "organization_id": org_id,
                **DEFAULT_BRANDING,
                "created_at": now,
                "updated_at": now
            }
            await db.organization_branding.insert_one(branding)
            branding.pop("_id", None)
        
        logger.info(f"Branding reset for org {org_id} by user {user_id}")
        return branding
    
    # =============================================
    # Logo Management
    # =============================================
    
    async def upload_logo(
        self,
        org_id: str,
        user_id: str,
        filename: str,
        content: bytes
    ) -> Tuple[bool, str, Optional[str]]:
        """Upload organization logo"""
        db = get_database()
        
        # Validate file extension
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}", None
        
        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            return False, "File too large. Maximum size is 1MB", None
        
        # Generate unique filename
        stored_filename = f"{org_id}_{uuid.uuid4().hex[:8]}{file_ext}"
        filepath = os.path.join(UPLOAD_DIR, stored_filename)
        
        # Save file
        with open(filepath, "wb") as f:
            f.write(content)
        
        logo_url = f"/api/branding/logo/{stored_filename}"
        now = datetime.now(timezone.utc).isoformat()
        
        existing = await db.organization_branding.find_one({"organization_id": org_id})
        
        if existing:
            # Delete old logo file if exists
            if existing.get("logo_url"):
                old_filename = existing["logo_url"].split("/")[-1]
                old_filepath = os.path.join(UPLOAD_DIR, old_filename)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            
            await db.organization_branding.update_one(
                {"organization_id": org_id},
                {"$set": {"logo_url": logo_url, "updated_at": now}}
            )
        else:
            branding_id = f"brand_{uuid.uuid4().hex[:12]}"
            branding = {
                "branding_id": branding_id,
                "organization_id": org_id,
                **DEFAULT_BRANDING,
                "logo_url": logo_url,
                "created_at": now,
                "updated_at": now
            }
            await db.organization_branding.insert_one(branding)
        
        await audit_service.log(
            user_id, org_id, "update", "branding",
            org_id,
            {"action": "logo_uploaded", "filename": stored_filename}
        )
        
        logger.info(f"Logo uploaded for org {org_id}: {stored_filename}")
        return True, "Logo uploaded", logo_url
    
    async def delete_logo(self, org_id: str, user_id: str) -> Tuple[bool, str]:
        """Delete organization logo"""
        db = get_database()
        
        existing = await db.organization_branding.find_one({"organization_id": org_id})
        
        if not existing or not existing.get("logo_url"):
            return False, "No logo found"
        
        # Delete file
        filename = existing["logo_url"].split("/")[-1]
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        
        now = datetime.now(timezone.utc).isoformat()
        
        await db.organization_branding.update_one(
            {"organization_id": org_id},
            {"$set": {"logo_url": None, "updated_at": now}}
        )
        
        await audit_service.log(
            user_id, org_id, "update", "branding",
            org_id,
            {"action": "logo_deleted"}
        )
        
        logger.info(f"Logo deleted for org {org_id}")
        return True, "Logo deleted successfully"
    
    def get_logo_path(self, filename: str) -> Optional[str]:
        """Get logo file path"""
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(filepath):
            return filepath
        return None
    
    def get_media_type(self, filename: str) -> str:
        """Get media type for a file"""
        ext = os.path.splitext(filename)[1].lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".webp": "image/webp"
        }
        return media_types.get(ext, "application/octet-stream")


# Singleton instance
branding_service = BrandingService()
