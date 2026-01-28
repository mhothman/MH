"""
ProFlow - Project Management SaaS Platform
Server entry point (backwards compatibility wrapper)

This file exists for backwards compatibility with existing infrastructure.
All application logic is now in main.py and the modular architecture.
"""
# Import the app from the new modular structure
from main import app

# This allows: uvicorn server:app
__all__ = ["app"]
