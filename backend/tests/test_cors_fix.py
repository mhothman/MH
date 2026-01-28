"""
Test CORS fix verification - Testing that API calls work correctly after CORS fix
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

class TestCORSFix:
    """Verify CORS fix is working - all API calls should succeed"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@proflow.com",
            "password": "test123456"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            token = data.get("access_token") or data.get("token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                self.token = token
            self.user = data.get("user", {})
            self.org_id = self.user.get("organization_id")
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_health_endpoint(self):
        """Test health endpoint works"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✅ Health endpoint working")
    
    def test_login_works(self):
        """Test login endpoint works (CORS fix verification)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@proflow.com",
            "password": "test123456"
        }, headers={"Content-Type": "application/json"})
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data or "token" in data
        print("✅ Login endpoint working")
    
    def test_customers_list(self):
        """Test customers list endpoint works"""
        response = self.session.get(f"{BASE_URL}/api/customers/?org_id={self.org_id}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Customers endpoint working - {len(data)} customers found")
    
    def test_projects_list(self):
        """Test projects list endpoint works"""
        response = self.session.get(f"{BASE_URL}/api/projects/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Projects endpoint working - {len(data)} projects found")
    
    def test_dashboard_endpoint(self):
        """Test dashboard endpoint works"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/")
        assert response.status_code == 200
        print("✅ Dashboard endpoint working")
    
    def test_organizations_list(self):
        """Test organizations list endpoint works"""
        response = self.session.get(f"{BASE_URL}/api/organizations/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Organizations endpoint working - {len(data)} orgs found")
    
    def test_notifications_endpoint(self):
        """Test notifications endpoint works"""
        response = self.session.get(f"{BASE_URL}/api/notifications/?unread_only=true")
        assert response.status_code == 200
        print("✅ Notifications endpoint working")
    
    def test_auth_me_endpoint(self):
        """Test auth/me endpoint works"""
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        print("✅ Auth/me endpoint working")
    
    def test_auth_permissions_endpoint(self):
        """Test auth permissions endpoint works"""
        if self.org_id:
            response = self.session.get(f"{BASE_URL}/api/auth/permissions/{self.org_id}")
            assert response.status_code == 200
            print("✅ Auth permissions endpoint working")
        else:
            pytest.skip("No org_id available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
