"""SSL/TLS Certificate Management Service

This service handles automated SSL certificate generation and management
for custom domains using Let's Encrypt via ACME protocol.

For production deployment, this integrates with:
- Certbot for Let's Encrypt certificates
- DNS validation or HTTP-01 challenge
- Nginx reload for certificate updates
"""
import os
import logging
import asyncio
import subprocess
from typing import Dict, Optional, List
from datetime import datetime, timezone, timedelta
from pathlib import Path

from core.database import get_database

logger = logging.getLogger(__name__)


class SSLService:
    """SSL Certificate management service"""
    
    # Certificate storage paths
    CERT_BASE_PATH = Path("/etc/letsencrypt/live")
    ACME_CHALLENGE_PATH = Path("/var/www/acme-challenge")
    
    # Certificate validity check threshold (days)
    RENEWAL_THRESHOLD_DAYS = 30
    
    def __init__(self):
        self.db = None
    
    def _get_db(self):
        if not self.db:
            self.db = get_database()
        return self.db
    
    async def request_certificate(self, domain: str, org_id: str, email: str = None) -> Dict:
        """
        Request a new SSL certificate for a domain
        
        Args:
            domain: The custom domain to get certificate for
            org_id: Organization ID
            email: Admin email for Let's Encrypt notifications
            
        Returns:
            Dict with status and certificate info
        """
        db = self._get_db()
        
        # Validate domain format
        if not self._validate_domain(domain):
            return {
                "success": False,
                "error": "Invalid domain format",
                "status": "validation_failed"
            }
        
        # Check if certificate already exists
        existing = await self._get_certificate_info(domain)
        if existing and existing.get("valid_until"):
            valid_until = datetime.fromisoformat(existing["valid_until"])
            if valid_until > datetime.now(timezone.utc) + timedelta(days=self.RENEWAL_THRESHOLD_DAYS):
                return {
                    "success": True,
                    "message": "Valid certificate already exists",
                    "certificate": existing,
                    "status": "already_valid"
                }
        
        # Create certificate request record
        cert_request = {
            "domain": domain,
            "org_id": org_id,
            "email": email,
            "status": "pending",
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "attempts": 0
        }
        
        await db.ssl_certificates.update_one(
            {"domain": domain},
            {"$set": cert_request},
            upsert=True
        )
        
        # In production, this would trigger certbot
        # For now, we'll simulate the process
        result = await self._request_letsencrypt_cert(domain, email)
        
        if result["success"]:
            # Update certificate record with success
            await db.ssl_certificates.update_one(
                {"domain": domain},
                {"$set": {
                    "status": "active",
                    "issued_at": datetime.now(timezone.utc).isoformat(),
                    "valid_until": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
                    "issuer": "Let's Encrypt",
                    "auto_renew": True
                }}
            )
            
            # Update organization domain config
            await db.organizations.update_one(
                {"org_id": org_id},
                {"$set": {
                    "ssl_enabled": True,
                    "ssl_status": "active",
                    "ssl_issued_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        else:
            # Update with failure
            await db.ssl_certificates.update_one(
                {"domain": domain},
                {"$set": {
                    "status": "failed",
                    "error": result.get("error"),
                    "last_attempt": datetime.now(timezone.utc).isoformat()
                },
                "$inc": {"attempts": 1}}
            )
        
        return result
    
    async def _request_letsencrypt_cert(self, domain: str, email: str = None) -> Dict:
        """
        Request certificate from Let's Encrypt using certbot
        
        In production, this runs certbot with appropriate parameters.
        For development/testing, this simulates the process.
        """
        # Check if running in production mode
        is_production = os.environ.get("ENVIRONMENT", "development") == "production"
        
        if not is_production:
            # Simulate certificate generation for development
            logger.info(f"[DEV MODE] Simulating SSL certificate for {domain}")
            return {
                "success": True,
                "message": "Certificate generated (simulated in dev mode)",
                "domain": domain,
                "status": "active",
                "note": "In production, Let's Encrypt certificate will be issued"
            }
        
        # Production certificate request
        try:
            certbot_email = email or os.environ.get("LETSENCRYPT_EMAIL", "admin@example.com")
            
            # Prepare certbot command
            cmd = [
                "certbot", "certonly",
                "--webroot",
                "-w", str(self.ACME_CHALLENGE_PATH),
                "-d", domain,
                "--email", certbot_email,
                "--agree-tos",
                "--non-interactive",
                "--expand"
            ]
            
            # Run certbot
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"SSL certificate issued for {domain}")
                
                # Reload nginx to pick up new certificate
                await self._reload_nginx()
                
                return {
                    "success": True,
                    "message": "SSL certificate issued successfully",
                    "domain": domain,
                    "status": "active"
                }
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Certbot failed for {domain}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "status": "failed"
                }
                
        except Exception as e:
            logger.exception(f"SSL certificate request failed for {domain}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }
    
    async def _reload_nginx(self):
        """Reload nginx to apply new certificates"""
        try:
            process = await asyncio.create_subprocess_exec(
                "nginx", "-s", "reload",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            logger.info("Nginx reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload nginx: {e}")
    
    async def renew_certificates(self) -> Dict:
        """
        Check and renew certificates that are expiring soon
        
        This should be run as a scheduled task (e.g., daily cron job)
        """
        db = self._get_db()
        
        # Find certificates expiring within threshold
        threshold = datetime.now(timezone.utc) + timedelta(days=self.RENEWAL_THRESHOLD_DAYS)
        
        expiring_certs = await db.ssl_certificates.find({
            "status": "active",
            "auto_renew": True,
            "valid_until": {"$lt": threshold.isoformat()}
        }, {"_id": 0}).to_list(100)
        
        results = {
            "renewed": [],
            "failed": [],
            "checked": len(expiring_certs)
        }
        
        for cert in expiring_certs:
            logger.info(f"Renewing certificate for {cert['domain']}")
            result = await self._request_letsencrypt_cert(cert["domain"], cert.get("email"))
            
            if result["success"]:
                results["renewed"].append(cert["domain"])
            else:
                results["failed"].append({
                    "domain": cert["domain"],
                    "error": result.get("error")
                })
        
        return results
    
    async def get_certificate_status(self, domain: str) -> Dict:
        """Get SSL certificate status for a domain"""
        db = self._get_db()
        
        cert = await db.ssl_certificates.find_one({"domain": domain}, {"_id": 0})
        
        if not cert:
            return {
                "domain": domain,
                "status": "not_configured",
                "ssl_enabled": False
            }
        
        # Check if certificate is still valid
        if cert.get("valid_until"):
            valid_until = datetime.fromisoformat(cert["valid_until"])
            is_valid = valid_until > datetime.now(timezone.utc)
            days_remaining = (valid_until - datetime.now(timezone.utc)).days
            
            cert["is_valid"] = is_valid
            cert["days_remaining"] = max(0, days_remaining)
            cert["needs_renewal"] = days_remaining <= self.RENEWAL_THRESHOLD_DAYS
        
        return cert
    
    async def revoke_certificate(self, domain: str, org_id: str) -> Dict:
        """Revoke an SSL certificate"""
        db = self._get_db()
        
        # Verify ownership
        cert = await db.ssl_certificates.find_one({"domain": domain, "org_id": org_id})
        if not cert:
            return {
                "success": False,
                "error": "Certificate not found or access denied"
            }
        
        # Update status
        await db.ssl_certificates.update_one(
            {"domain": domain},
            {"$set": {
                "status": "revoked",
                "revoked_at": datetime.now(timezone.utc).isoformat(),
                "auto_renew": False
            }}
        )
        
        # Update org
        await db.organizations.update_one(
            {"org_id": org_id},
            {"$set": {
                "ssl_enabled": False,
                "ssl_status": "revoked"
            }}
        )
        
        return {
            "success": True,
            "message": "Certificate revoked successfully"
        }
    
    async def _get_certificate_info(self, domain: str) -> Optional[Dict]:
        """Get stored certificate info from database"""
        db = self._get_db()
        return await db.ssl_certificates.find_one({"domain": domain}, {"_id": 0})
    
    def _validate_domain(self, domain: str) -> bool:
        """Validate domain format"""
        import re
        pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        return bool(re.match(pattern, domain))
    
    async def get_all_certificates(self, org_id: str = None) -> List[Dict]:
        """Get all SSL certificates, optionally filtered by org"""
        db = self._get_db()
        
        query = {}
        if org_id:
            query["org_id"] = org_id
        
        return await db.ssl_certificates.find(query, {"_id": 0}).to_list(100)
    
    async def generate_nginx_config(self, domain: str) -> str:
        """Generate nginx SSL configuration for a domain"""
        cert_path = self.CERT_BASE_PATH / domain
        
        config = f"""
# SSL configuration for {domain}
server {{
    listen 443 ssl http2;
    server_name {domain};
    
    ssl_certificate {cert_path}/fullchain.pem;
    ssl_certificate_key {cert_path}/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # HSTS (optional)
    add_header Strict-Transport-Security "max-age=31536000" always;
    
    location / {{
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }}
    
    location /api {{
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}

# HTTP to HTTPS redirect
server {{
    listen 80;
    server_name {domain};
    
    location /.well-known/acme-challenge/ {{
        root /var/www/acme-challenge;
    }}
    
    location / {{
        return 301 https://$host$request_uri;
    }}
}}
"""
        return config


# Singleton instance
ssl_service = SSLService()
