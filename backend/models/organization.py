"""Organization-related models with validation"""
from pydantic import BaseModel, ConfigDict, field_validator, EmailStr
from typing import Optional, List
from datetime import datetime
import re
import pytz


# Valid working days
VALID_WORKING_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}

# Common timezones (subset for validation)
def is_valid_timezone(tz: str) -> bool:
    """Check if timezone is valid"""
    try:
        pytz.timezone(tz)
        return True
    except pytz.UnknownTimeZoneError:
        return False


class OrganizationCreate(BaseModel):
    name: str
    logo: Optional[str] = None
    timezone: str = "UTC"
    working_days: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Organization name cannot be empty')
        if len(v.strip()) > 100:
            raise ValueError('Organization name cannot exceed 100 characters')
        return v.strip()
    
    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if not is_valid_timezone(v):
            raise ValueError(f'Invalid timezone: {v}')
        return v
    
    @field_validator('working_days')
    @classmethod
    def validate_working_days(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError('At least one working day must be specified')
        invalid_days = set(d.lower() for d in v) - VALID_WORKING_DAYS
        if invalid_days:
            raise ValueError(f'Invalid working days: {", ".join(invalid_days)}. Must be one of: {", ".join(VALID_WORKING_DAYS)}')
        return [d.lower() for d in v]
    
    @field_validator('logo')
    @classmethod
    def validate_logo(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 2000:
            raise ValueError('Logo URL cannot exceed 2000 characters')
        return v


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    logo: Optional[str] = None
    timezone: Optional[str] = None
    working_days: Optional[List[str]] = None
    address: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError('Organization name cannot be empty')
            if len(v.strip()) > 100:
                raise ValueError('Organization name cannot exceed 100 characters')
            return v.strip()
        return v
    
    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not is_valid_timezone(v):
            raise ValueError(f'Invalid timezone: {v}')
        return v
    
    @field_validator('working_days')
    @classmethod
    def validate_working_days(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            if not v:
                raise ValueError('At least one working day must be specified')
            invalid_days = set(d.lower() for d in v) - VALID_WORKING_DAYS
            if invalid_days:
                raise ValueError(f'Invalid working days: {", ".join(invalid_days)}')
            return [d.lower() for d in v]
        return v
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 500:
            raise ValueError('Address cannot exceed 500 characters')
        return v
    
    @field_validator('contact_phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Remove common formatting characters
            cleaned = re.sub(r'[\s\-\(\)\.]', '', v)
            if len(cleaned) > 20:
                raise ValueError('Phone number too long')
            if cleaned and not re.match(r'^\+?[0-9]+$', cleaned):
                raise ValueError('Invalid phone number format')
        return v
    
    @field_validator('contact_email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Basic email validation
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
                raise ValueError('Invalid email format')
            if len(v) > 254:
                raise ValueError('Email cannot exceed 254 characters')
        return v
    
    @field_validator('logo')
    @classmethod
    def validate_logo(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 2000:
            raise ValueError('Logo URL cannot exceed 2000 characters')
        return v


class InviteCreate(BaseModel):
    email: str
    role: str = "team_member"
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Email is required')
        v = v.strip().lower()
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        if len(v) > 254:
            raise ValueError('Email cannot exceed 254 characters')
        return v
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = {"team_member", "project_manager", "finance", "org_admin", "super_admin", "viewer"}
        if v not in valid_roles:
            raise ValueError(f'Invalid role. Must be one of: {", ".join(valid_roles)}')
        return v


class ChangeRoleRequest(BaseModel):
    role: Optional[str] = None
    custom_role_id: Optional[str] = None  # For assigning custom roles
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_roles = {"team_member", "project_manager", "finance", "org_admin", "super_admin", "viewer"}
            if v not in valid_roles:
                raise ValueError(f'Invalid role. Must be one of: {", ".join(valid_roles)}')
        return v


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    org_id: str
    name: str
    logo: Optional[str] = None
    timezone: str
    working_days: List[str]
    owner_id: str
    address: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    # White-label domain
    custom_domain: Optional[str] = None
    domain_verified: bool = False
    domain_verification_token: Optional[str] = None
    created_at: datetime


class MemberResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    org_role: str
    custom_role_id: Optional[str] = None
    custom_role_name: Optional[str] = None
    is_owner: bool = False
    suspended: bool = False
    joined_at: Optional[str] = None
    created_at: datetime


# White-Label Domain Models
class DomainConfigRequest(BaseModel):
    """Request to configure a custom domain"""
    custom_domain: str
    
    @field_validator('custom_domain')
    @classmethod
    def validate_domain(cls, v):
        # Basic domain validation
        if not v:
            raise ValueError('Domain cannot be empty')
        # Remove protocol if present
        v = re.sub(r'^https?://', '', v)
        # Remove trailing slash
        v = v.rstrip('/')
        # Basic domain pattern
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)+$'
        if not re.match(domain_pattern, v):
            raise ValueError('Invalid domain format')
        if len(v) > 253:
            raise ValueError('Domain cannot exceed 253 characters')
        return v.lower()


class DomainVerificationResponse(BaseModel):
    """Domain verification status and instructions"""
    custom_domain: Optional[str] = None
    domain_verified: bool = False
    verification_token: Optional[str] = None
    verification_instructions: Optional[str] = None
    dns_records: Optional[List[dict]] = None


class DomainVerifyRequest(BaseModel):
    """Request to verify domain ownership"""
    pass  # No body needed, just triggers verification
