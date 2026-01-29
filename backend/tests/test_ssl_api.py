"""
SSL API Tests - Testing SSL certificate management endpoints
Tests for Phase 3 architecture refactoring + SSL automation feature
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://docflows.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "test@proflow.com"
TEST_PASSWORD = "test123456"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture(scope="module")
def org_id(auth_token):
    """Get organization ID for the test user"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = requests.get(f"{BASE_URL}/api/organizations/", headers=headers)
    if response.status_code == 200:
        orgs = response.json()
        if orgs:
            return orgs[0].get("org_id")
    pytest.skip("No organization found - skipping tests")


class TestSSLStatusAPI:
    """Tests for SSL status endpoint"""
    
    def test_ssl_status_returns_200(self, auth_token, org_id):
        """SSL status endpoint should return 200 for authenticated users"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/ssl/org/{org_id}/status", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "status" in data
        assert "ssl_enabled" in data
        print(f"SSL Status: {data}")
    
    def test_ssl_status_no_domain_configured(self, auth_token, org_id):
        """SSL status should indicate no custom domain when none is configured"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/ssl/org/{org_id}/status", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # When no domain is configured, status should be "no_custom_domain"
        assert data.get("status") == "no_custom_domain"
        assert data.get("ssl_enabled") == False
        assert "message" in data
    
    def test_ssl_status_requires_auth(self, org_id):
        """SSL status endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/ssl/org/{org_id}/status")
        
        assert response.status_code == 401
    
    def test_ssl_status_invalid_org(self, auth_token):
        """SSL status should return 404 for invalid org"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/ssl/org/invalid_org_id/status", headers=headers)
        
        # Should return 403 (access denied) or 404 (not found)
        assert response.status_code in [403, 404]


class TestSSLRequestAPI:
    """Tests for SSL certificate request endpoint"""
    
    def test_ssl_request_requires_domain(self, auth_token, org_id):
        """SSL request should fail if no domain is configured"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(
            f"{BASE_URL}/api/ssl/org/{org_id}/request",
            headers=headers,
            json={"domain": "test.example.com"}
        )
        
        # Should fail because domain is not configured for the org
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    
    def test_ssl_request_requires_auth(self, org_id):
        """SSL request endpoint should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/ssl/org/{org_id}/request",
            json={"domain": "test.example.com"}
        )
        
        assert response.status_code == 401


class TestSSLRenewalAPI:
    """Tests for SSL certificate renewal endpoint"""
    
    def test_ssl_renew_requires_domain(self, auth_token, org_id):
        """SSL renewal should fail if no domain is configured"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(
            f"{BASE_URL}/api/ssl/org/{org_id}/renew",
            headers=headers,
            json={}
        )
        
        # Should fail because no domain is configured
        assert response.status_code == 400
    
    def test_ssl_renew_requires_auth(self, org_id):
        """SSL renewal endpoint should require authentication"""
        response = requests.post(f"{BASE_URL}/api/ssl/org/{org_id}/renew", json={})
        
        assert response.status_code == 401


class TestSSLNginxConfigAPI:
    """Tests for nginx config generation endpoint"""
    
    def test_nginx_config_requires_domain(self, auth_token, org_id):
        """Nginx config should fail if no domain is configured"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/ssl/org/{org_id}/nginx-config",
            headers=headers
        )
        
        # Should fail because no domain is configured
        assert response.status_code == 400
    
    def test_nginx_config_requires_auth(self, org_id):
        """Nginx config endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/ssl/org/{org_id}/nginx-config")
        
        assert response.status_code == 401


class TestExistingFunctionality:
    """Tests to verify existing functionality still works"""
    
    def test_dashboard_stats(self, auth_token):
        """Dashboard stats should still work"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "tasks" in data
    
    def test_projects_list(self, auth_token, org_id):
        """Projects list should still work"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/projects/?org_id={org_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_customers_list(self, auth_token, org_id):
        """Customers list should still work (previous bug fix)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/customers/?org_id={org_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_customer_crud_create(self, auth_token, org_id):
        """Customer creation should work (previous bug fix verification)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create customer - org_id is a query parameter
        customer_data = {
            "name": "TEST_SSL_Customer",
            "email": "ssl_test@example.com",
            "phone": "+1-555-SSL-TEST",
            "company": "SSL Test Company"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/customers/?org_id={org_id}",
            headers=headers,
            json=customer_data
        )
        
        assert response.status_code in [200, 201]  # Accept both 200 and 201
        data = response.json()
        
        # Verify no MongoDB _id leak (previous bug)
        assert "_id" not in data
        assert "customer_id" in data
        
        # Cleanup - delete the test customer
        customer_id = data["customer_id"]
        delete_response = requests.delete(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers=headers
        )
        assert delete_response.status_code in [200, 204]


class TestHealthEndpoints:
    """Tests for health check endpoints"""
    
    def test_health_check(self):
        """Health check should return healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
    
    def test_root_health_check(self):
        """Root health check should also work"""
        # Note: /health without /api prefix may not be routed through ingress
        # Testing /api/health instead which is the primary health endpoint
        response = requests.get(f"{BASE_URL}/api/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
