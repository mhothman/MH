"""Application configuration management"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache

ROOT_DIR = Path(__file__).parent.parent

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    MONGO_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "proflow_db"
    
    # JWT
    JWT_SECRET: str = "proflow-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # CORS
    CORS_ORIGINS: str = "*"
    
    # Email
    RESEND_API_KEY: str = ""
    SENDER_EMAIL: str = "onboarding@resend.dev"
    
    # App
    APP_NAME: str = "ProFlow"
    APP_URL: str = ""  # Set via environment variable for deployment
    FRONTEND_URL: str = ""  # Set via environment variable for email links
    DEBUG: bool = False
    
    class Config:
        env_file = str(ROOT_DIR / ".env")
        extra = "allow"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

settings = get_settings()
