"""Organization Branding Models"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re

# Preset Google Fonts
PRESET_FONTS = [
    {"id": "inter", "name": "Inter", "url": "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"},
    {"id": "roboto", "name": "Roboto", "url": "https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap"},
    {"id": "poppins", "name": "Poppins", "url": "https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap"},
    {"id": "open-sans", "name": "Open Sans", "url": "https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;500;600;700&display=swap"},
    {"id": "lato", "name": "Lato", "url": "https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&display=swap"},
    {"id": "montserrat", "name": "Montserrat", "url": "https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap"},
    {"id": "nunito", "name": "Nunito", "url": "https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;500;600;700&display=swap"},
    {"id": "raleway", "name": "Raleway", "url": "https://fonts.googleapis.com/css2?family=Raleway:wght@300;400;500;600;700&display=swap"},
    {"id": "source-sans", "name": "Source Sans Pro", "url": "https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap"},
    {"id": "playfair", "name": "Playfair Display", "url": "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&display=swap"},
    {"id": "merriweather", "name": "Merriweather", "url": "https://fonts.googleapis.com/css2?family=Merriweather:wght@300;400;700&display=swap"},
    {"id": "dm-sans", "name": "DM Sans", "url": "https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap"},
]

# Preset Theme Templates
PRESET_THEMES = [
    {
        "id": "corporate-blue",
        "name": "Corporate Blue",
        "description": "Professional and trustworthy - perfect for enterprise",
        "primary_color": "#1e3a5f",
        "secondary_color": "#3b82f6",
        "accent_color": "#10b981",
        "heading_font": "inter",
        "body_font": "inter"
    },
    {
        "id": "modern-green",
        "name": "Modern Green",
        "description": "Fresh and eco-friendly - great for sustainability",
        "primary_color": "#064e3b",
        "secondary_color": "#10b981",
        "accent_color": "#3b82f6",
        "heading_font": "poppins",
        "body_font": "open-sans"
    },
    {
        "id": "elegant-dark",
        "name": "Elegant Dark",
        "description": "Sophisticated and premium - ideal for luxury brands",
        "primary_color": "#0f0f0f",
        "secondary_color": "#6366f1",
        "accent_color": "#f59e0b",
        "heading_font": "playfair",
        "body_font": "lato"
    },
    {
        "id": "warm-sunset",
        "name": "Warm Sunset",
        "description": "Energetic and creative - perfect for startups",
        "primary_color": "#7c2d12",
        "secondary_color": "#f97316",
        "accent_color": "#fbbf24",
        "heading_font": "montserrat",
        "body_font": "nunito"
    },
    {
        "id": "professional-gray",
        "name": "Professional Gray",
        "description": "Neutral and balanced - suits any industry",
        "primary_color": "#374151",
        "secondary_color": "#6b7280",
        "accent_color": "#8b5cf6",
        "heading_font": "roboto",
        "body_font": "roboto"
    },
    {
        "id": "ocean-breeze",
        "name": "Ocean Breeze",
        "description": "Calm and refreshing - great for tech and SaaS",
        "primary_color": "#0c4a6e",
        "secondary_color": "#0ea5e9",
        "accent_color": "#06b6d4",
        "heading_font": "dm-sans",
        "body_font": "inter"
    }
]

# Blocked CSS selectors for security
BLOCKED_SELECTORS = [
    "html", "body", ":root", "*", "head", "script", "style", "link", "meta",
    "@import", "@font-face", "@keyframes"
]

MAX_CUSTOM_CSS_LENGTH = 10240  # 10KB limit

class FontSettings(BaseModel):
    """Font configuration"""
    heading_font: str = "inter"  # Font ID or "custom"
    heading_font_url: Optional[str] = None  # Custom font URL
    body_font: str = "inter"
    body_font_url: Optional[str] = None

class BrandingBase(BaseModel):
    """Base branding fields"""
    logo_url: Optional[str] = None
    primary_color: str = "#0f172a"
    secondary_color: str = "#3b82f6"
    accent_color: str = "#10b981"
    dark_mode_supported: bool = True
    # Font settings
    heading_font: str = "inter"
    heading_font_url: Optional[str] = None
    body_font: str = "inter"
    body_font_url: Optional[str] = None
    # Custom CSS
    custom_css: Optional[str] = None

class BrandingCreate(BrandingBase):
    """Create branding request"""
    pass

class BrandingUpdate(BaseModel):
    """Update branding request"""
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    dark_mode_supported: Optional[bool] = None
    heading_font: Optional[str] = None
    heading_font_url: Optional[str] = None
    body_font: Optional[str] = None
    body_font_url: Optional[str] = None
    custom_css: Optional[str] = None

    @field_validator('custom_css')
    @classmethod
    def validate_custom_css(cls, v):
        if v is None:
            return v
        if len(v) > MAX_CUSTOM_CSS_LENGTH:
            raise ValueError(f'Custom CSS exceeds maximum length of {MAX_CUSTOM_CSS_LENGTH} characters')
        # Check for blocked selectors
        css_lower = v.lower()
        for selector in BLOCKED_SELECTORS:
            if selector in css_lower:
                raise ValueError(f'CSS contains blocked selector or rule: {selector}')
        return v

class BrandingResponse(BrandingBase):
    """Branding response"""
    branding_id: str
    organization_id: str
    published: bool = False
    created_at: datetime
    updated_at: datetime

class BrandingPublic(BaseModel):
    """Public branding data (for non-admins)"""
    logo_url: Optional[str] = None
    primary_color: str
    secondary_color: str
    accent_color: str
    dark_mode_supported: bool
    organization_name: str
    # Font settings
    heading_font: str = "inter"
    heading_font_url: Optional[str] = None
    body_font: str = "inter"
    body_font_url: Optional[str] = None
    # Custom CSS (sanitized)
    custom_css: Optional[str] = None

class PresetFontsResponse(BaseModel):
    """List of available preset fonts"""
    fonts: List[dict]
