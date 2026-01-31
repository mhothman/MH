"""Organization Service - Business logic for organization management"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
import uuid
import hashlib
import logging
import dns.resolver

from core.database import get_database
from core.config import settings
from repositories.organization_repository import organization_repository
from services.email_service import email_service
from services.audit_service import audit_service
from services.feature_service import feature_service

logger = logging.getLogger(__name__)


class OrganizationService:
    """Service for organization business logic"""
    
    def __init__(self):
        self.repo = organization_repository
    
    # =============================================
    # Organization CRUD
    # =============================================
    
    async def get_user_organizations(self, user_id: str) -> List[Dict]:
        """Get all organizations for a user"""
        return await self.repo.get_user_organizations(user_id)
    
    async def get_organization(self, org_id: str) -> Optional[Dict]:
        """Get organization by ID"""
        org = await self.repo.find_by_id(org_id)
        if org:
            org["created_at"] = self._parse_datetime(org.get("created_at"))
        return org
    
    async def update_organization(
        self, 
        org_id: str, 
        user_id: str,
        name: str = None,
        logo: str = None,
        timezone_str: str = None,
        working_days: List[str] = None,
        address: str = None,
        contact_phone: str = None,
        contact_email: str = None
    ) -> Optional[Dict]:
        """Update organization settings"""
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if logo is not None:
            update_data["logo"] = logo
        if timezone_str is not None:
            update_data["timezone"] = timezone_str
        if working_days is not None:
            update_data["working_days"] = working_days
        if address is not None:
            update_data["address"] = address
        if contact_phone is not None:
            update_data["contact_phone"] = contact_phone
        if contact_email is not None:
            update_data["contact_email"] = contact_email
        
        if update_data:
            await self.repo.update(org_id, update_data)
            await audit_service.log(
                user_id, org_id, "update", "organization", org_id,
                {"updated_fields": list(update_data.keys())}
            )
        
        return await self.get_organization(org_id)
    
    # =============================================
    # Member Management
    # =============================================
    
    async def get_members(self, org_id: str) -> List[Dict]:
        """Get all members of an organization with user details"""
        db = get_database()
        
        memberships = await db.org_memberships.find({"org_id": org_id}, {"_id": 0}).to_list(200)
        if not memberships:
            return []
        
        user_ids = [m["user_id"] for m in memberships]
        users = await db.users.find(
            {"user_id": {"$in": user_ids}}, 
            {"_id": 0, "password_hash": 0}
        ).to_list(200)
        
        org = await self.repo.find_by_id(org_id)
        membership_map = {m["user_id"]: m for m in memberships}
        
        result = []
        for u in users:
            member_data = membership_map.get(u["user_id"], {})
            u["org_role"] = member_data.get("role", "team_member")
            u["is_owner"] = org and org.get("owner_id") == u["user_id"]
            u["suspended"] = u.get("suspended", False)
            u["joined_at"] = member_data.get("joined_at")
            u["created_at"] = self._parse_datetime(u.get("created_at"))
            u["custom_role_id"] = member_data.get("custom_role_id")
            u["custom_role_name"] = member_data.get("custom_role_name")
            result.append(u)
        
        return result
    
    async def invite_member(
        self, 
        org_id: str, 
        inviter_id: str,
        inviter_name: str,
        email: str, 
        role: str
    ) -> Tuple[bool, str]:
        """
        Invite a user to the organization.
        Returns: (success, message)
        """
        db = get_database()
        
        # Check member limit
        current_members = await db.org_memberships.count_documents({"org_id": org_id})
        can_add = await feature_service.check_limit(org_id, "max_members", current_members)
        if not can_add:
            return False, "Member limit reached for your plan"
        
        org = await self.repo.find_by_id(org_id)
        if not org:
            return False, "Organization not found"
        
        # Check if user already exists
        existing_user = await db.users.find_one({"email": email}, {"_id": 0})
        
        if existing_user:
            # Check if already a member
            existing_membership = await self.repo.get_user_membership(existing_user["user_id"], org_id)
            if existing_membership:
                return False, "User is already a member"
            
            # Add existing user directly
            await db.org_memberships.insert_one({
                "membership_id": f"mem_{uuid.uuid4().hex[:12]}",
                "user_id": existing_user["user_id"],
                "org_id": org_id,
                "role": role,
                "joined_at": datetime.now(timezone.utc).isoformat()
            })
            
            await audit_service.log(inviter_id, org_id, "invite", "member", existing_user["user_id"])
            return True, "Member added successfully"
        else:
            # Create invitation for new user
            invite_token = f"inv_{uuid.uuid4().hex}"
            invitation = {
                "invite_id": f"invite_{uuid.uuid4().hex[:12]}",
                "token": invite_token,
                "email": email,
                "org_id": org_id,
                "role": role,
                "invited_by": inviter_id,
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "accepted": False
            }
            await db.invitations.insert_one(invitation)
            
            # Send invitation email
            signup_link = f"{settings.APP_URL}/register?invite={invite_token}&email={email}"
            await email_service.send_invitation(email, org["name"], inviter_name, role, signup_link)
            
            await audit_service.log(inviter_id, org_id, "invite", "invitation", email)
            return True, "Invitation sent successfully"
    
    async def remove_member(self, org_id: str, user_id: str, remover_id: str) -> Tuple[bool, str]:
        """Remove a member from the organization"""
        db = get_database()
        
        # Check if trying to remove owner
        org = await self.repo.find_by_id(org_id)
        if org and org.get("owner_id") == user_id:
            return False, "Cannot remove organization owner"
        
        result = await db.org_memberships.delete_one({"org_id": org_id, "user_id": user_id})
        if result.deleted_count == 0:
            return False, "Member not found"
        
        await audit_service.log(remover_id, org_id, "remove", "member", user_id)
        return True, "Member removed successfully"
    
    async def suspend_member(self, org_id: str, user_id: str, admin_id: str) -> Tuple[bool, str]:
        """Suspend a member"""
        db = get_database()
        
        result = await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"suspended": True, "suspended_at": datetime.now(timezone.utc).isoformat()}}
        )
        if result.modified_count == 0:
            return False, "User not found"
        
        await audit_service.log(admin_id, org_id, "suspend", "member", user_id)
        return True, "Member suspended successfully"
    
    async def unsuspend_member(self, org_id: str, user_id: str, admin_id: str) -> Tuple[bool, str]:
        """Unsuspend a member"""
        db = get_database()
        
        result = await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"suspended": False}, "$unset": {"suspended_at": ""}}
        )
        if result.modified_count == 0:
            return False, "User not found"
        
        await audit_service.log(admin_id, org_id, "unsuspend", "member", user_id)
        return True, "Member unsuspended successfully"
    
    async def change_member_role(
        self, 
        org_id: str, 
        user_id: str, 
        admin_id: str,
        role: str = None,
        custom_role_id: str = None
    ) -> Tuple[bool, str]:
        """Change a member's role"""
        db = get_database()
        
        # Check if trying to change owner's role
        org = await self.repo.find_by_id(org_id)
        if org and org.get("owner_id") == user_id:
            return False, "Cannot change organization owner's role"
        
        if custom_role_id:
            # Verify custom role exists
            custom_role = await db.custom_roles.find_one({
                "role_id": custom_role_id,
                "org_id": org_id
            }, {"_id": 0})
            if not custom_role:
                return False, "Custom role not found"
            
            result = await db.org_memberships.update_one(
                {"org_id": org_id, "user_id": user_id},
                {"$set": {
                    "role": "team_member",
                    "custom_role_id": custom_role_id,
                    "custom_role_name": custom_role["name"]
                }}
            )
            role_ref = custom_role_id
        else:
            valid_roles = ["super_admin", "org_admin", "project_manager", "finance", "team_member", "viewer"]
            if role not in valid_roles:
                return False, "Invalid role"
            
            result = await db.org_memberships.update_one(
                {"org_id": org_id, "user_id": user_id},
                {
                    "$set": {"role": role},
                    "$unset": {"custom_role_id": "", "custom_role_name": ""}
                }
            )
            role_ref = role
        
        if result.modified_count == 0:
            return False, "Member not found"
        
        await audit_service.log(admin_id, org_id, "change_role", "member", f"{user_id}:{role_ref}")
        return True, "Role updated successfully"
    
    async def reset_member_password(
        self, 
        org_id: str, 
        user_id: str, 
        admin_id: str
    ) -> Tuple[bool, str]:
        """Send password reset email for a member"""
        db = get_database()
        
        target_user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not target_user:
            return False, "User not found"
        
        reset_token = f"rst_{uuid.uuid4().hex}"
        reset_data = {
            "token": reset_token,
            "user_id": user_id,
            "email": target_user["email"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.password_resets.insert_one(reset_data)
        
        reset_link = f"{settings.APP_URL}/reset-password?token={reset_token}"
        await email_service.send_password_reset(target_user["email"], reset_link, target_user["name"])
        
        await audit_service.log(admin_id, org_id, "reset_password", "member", user_id)
        return True, "Password reset email sent"
    
    # =============================================
    # Invitations
    # =============================================
    
    async def get_pending_invitations(self, org_id: str) -> List[Dict]:
        """Get all pending invitations"""
        db = get_database()
        return await db.invitations.find({
            "org_id": org_id,
            "accepted": False
        }, {"_id": 0}).to_list(100)
    
    async def resend_invitation(
        self, 
        org_id: str, 
        email: str, 
        sender_id: str,
        sender_name: str
    ) -> Tuple[bool, str]:
        """Resend an invitation email"""
        db = get_database()
        
        invitation = await db.invitations.find_one({
            "org_id": org_id,
            "email": email,
            "accepted": False
        }, {"_id": 0})
        
        if not invitation:
            return False, "No pending invitation found for this email"
        
        # Renew token if expired
        expires_at = datetime.fromisoformat(invitation["expires_at"].replace("Z", "+00:00"))
        if expires_at < datetime.now(timezone.utc):
            new_token = f"inv_{uuid.uuid4().hex}"
            await db.invitations.update_one(
                {"invite_id": invitation["invite_id"]},
                {"$set": {
                    "token": new_token,
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                }}
            )
            invitation["token"] = new_token
        
        org = await self.repo.find_by_id(org_id)
        signup_link = f"{settings.APP_URL}/register?invite={invitation['token']}&email={email}"
        await email_service.send_invitation(email, org["name"], sender_name, invitation["role"], signup_link)
        
        return True, "Invitation resent successfully"
    
    async def cancel_invitation(self, org_id: str, invite_id: str) -> Tuple[bool, str]:
        """Cancel a pending invitation"""
        db = get_database()
        result = await db.invitations.delete_one({"invite_id": invite_id, "org_id": org_id})
        if result.deleted_count == 0:
            return False, "Invitation not found"
        return True, "Invitation cancelled"
    
    # =============================================
    # Domain Management
    # =============================================
    
    def _generate_verification_token(self, org_id: str) -> str:
        """Generate a unique verification token for domain ownership"""
        return hashlib.sha256(f"proflow-verify-{org_id}-{uuid.uuid4().hex}".encode()).hexdigest()[:32]
    
    async def get_domain_config(self, org_id: str) -> Dict:
        """Get current domain configuration and verification status"""
        org = await self.repo.find_by_id(org_id)
        if not org:
            return None
        
        custom_domain = org.get("custom_domain")
        verified = org.get("domain_verified", False)
        token = org.get("domain_verification_token")
        
        instructions = None
        dns_records = None
        
        if custom_domain and not verified:
            instructions = f"""To verify ownership of {custom_domain}, add the following DNS TXT record:

Host/Name: _proflow-verification.{custom_domain}
Type: TXT
Value: proflow-verify={token}

After adding the record, click "Verify Domain" to complete verification.
DNS changes may take up to 48 hours to propagate."""
            
            dns_records = [
                {
                    "type": "TXT",
                    "host": f"_proflow-verification.{custom_domain}",
                    "value": f"proflow-verify={token}"
                },
                {
                    "type": "CNAME",
                    "host": custom_domain,
                    "value": "app.proflow.com",
                    "note": "Required for routing (add after verification)"
                }
            ]
        
        return {
            "custom_domain": custom_domain,
            "domain_verified": verified,
            "verification_token": token if not verified else None,
            "verification_instructions": instructions,
            "dns_records": dns_records
        }
    
    async def configure_domain(
        self, 
        org_id: str, 
        user_id: str,
        custom_domain: str
    ) -> Tuple[bool, str, Dict]:
        """Configure a custom domain for the organization"""
        db = get_database()
        
        # Check if domain is already in use
        existing = await db.organizations.find_one({
            "custom_domain": custom_domain,
            "org_id": {"$ne": org_id}
        })
        if existing:
            return False, "This domain is already in use by another organization", {}
        
        token = self._generate_verification_token(org_id)
        now = datetime.now(timezone.utc).isoformat()
        
        await db.organizations.update_one(
            {"org_id": org_id},
            {"$set": {
                "custom_domain": custom_domain,
                "domain_verified": False,
                "domain_verification_token": token,
                "updated_at": now
            }}
        )
        
        await audit_service.log(
            user_id, org_id, "update", "organization", org_id,
            {"action": "domain_configured", "domain": custom_domain}
        )
        
        logger.info(f"Domain {custom_domain} configured for org {org_id}")
        
        return True, "Domain configured successfully", {
            "custom_domain": custom_domain,
            "verification_token": token,
            "instructions": f"Add a TXT record for _proflow-verification.{custom_domain} with value: proflow-verify={token}"
        }
    
    async def verify_domain(self, org_id: str, user_id: str) -> Dict:
        """Verify domain ownership by checking DNS TXT record"""
        db = get_database()
        
        org = await self.repo.find_by_id(org_id)
        if not org:
            return {"verified": False, "message": "Organization not found"}
        
        custom_domain = org.get("custom_domain")
        if not custom_domain:
            return {"verified": False, "message": "No custom domain configured"}
        
        if org.get("domain_verified"):
            return {"verified": True, "message": "Domain already verified"}
        
        token = org.get("domain_verification_token")
        expected_value = f"proflow-verify={token}"
        
        try:
            txt_records = dns.resolver.resolve(f"_proflow-verification.{custom_domain}", "TXT")
            verified = False
            for record in txt_records:
                record_value = str(record).strip('"\'')
                if record_value == expected_value:
                    verified = True
                    break
            
            if verified:
                now = datetime.now(timezone.utc).isoformat()
                await db.organizations.update_one(
                    {"org_id": org_id},
                    {"$set": {
                        "domain_verified": True,
                        "domain_verified_at": now,
                        "updated_at": now
                    }}
                )
                
                await audit_service.log(
                    user_id, org_id, "update", "organization", org_id,
                    {"action": "domain_verified", "domain": custom_domain}
                )
                
                logger.info(f"Domain {custom_domain} verified for org {org_id}")
                
                return {
                    "verified": True,
                    "message": "Domain verified successfully!",
                    "custom_domain": custom_domain
                }
            else:
                return {
                    "verified": False,
                    "message": "Verification failed. TXT record not found or incorrect value.",
                    "expected_record": f"_proflow-verification.{custom_domain}",
                    "expected_value": expected_value
                }
                
        except dns.resolver.NXDOMAIN:
            return {
                "verified": False,
                "message": "DNS record not found. Please add the TXT record and wait for DNS propagation.",
                "expected_record": f"_proflow-verification.{custom_domain}",
                "expected_value": expected_value
            }
        except dns.resolver.NoAnswer:
            return {
                "verified": False,
                "message": "No TXT records found. Please add the verification record."
            }
        except Exception as e:
            logger.error(f"DNS verification error for {custom_domain}: {e}")
            return {
                "verified": False,
                "message": f"DNS lookup failed: {str(e)}"
            }
    
    async def remove_domain(self, org_id: str, user_id: str) -> Tuple[bool, str]:
        """Remove custom domain configuration"""
        db = get_database()
        
        org = await self.repo.find_by_id(org_id)
        if not org or not org.get("custom_domain"):
            return False, "No custom domain configured"
        
        old_domain = org.get("custom_domain")
        now = datetime.now(timezone.utc).isoformat()
        
        await db.organizations.update_one(
            {"org_id": org_id},
            {"$set": {
                "custom_domain": None,
                "domain_verified": False,
                "domain_verification_token": None,
                "updated_at": now
            }}
        )
        
        await audit_service.log(
            user_id, org_id, "update", "organization", org_id,
            {"action": "domain_removed", "domain": old_domain}
        )
        
        logger.info(f"Domain {old_domain} removed from org {org_id}")
        return True, "Custom domain removed successfully"
    
    # =============================================
    # Utilities
    # =============================================
    
    def _parse_datetime(self, dt_value) -> datetime:
        """Parse datetime from string or return as-is"""
        if isinstance(dt_value, str):
            return datetime.fromisoformat(dt_value.replace("Z", "+00:00"))
        return dt_value


# Singleton instance
organization_service = OrganizationService()
