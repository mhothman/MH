"""
Architecture Refactoring Tests
Tests for verifying the API modules and repository pattern work correctly after refactoring.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://approvalmate-3.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "test@proflow.com"
TEST_PASSWORD = "test123456"


class TestHealthEndpoint:
    """Test health endpoint - basic connectivity"""
    
    def test_health_endpoint_returns_200(self):
        """Health endpoint should return 200 with status healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        print(f"✓ Health endpoint working - version: {data['version']}")


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_login_with_valid_credentials(self):
        """Login should work with test credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print(f"✓ Login successful for {TEST_EMAIL}")
        return data["access_token"]
    
    def test_login_with_invalid_credentials(self):
        """Login should fail with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [401, 404]
        print("✓ Invalid login correctly rejected")
    
    def test_get_me_with_token(self):
        """Get current user with valid token"""
        # First login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = login_response.json()["access_token"]
        
        # Get me
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_EMAIL
        print(f"✓ Get me endpoint working - user: {data['email']}")


class TestProjectsAPI:
    """Test projects API endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def org_id(self, auth_token):
        """Get organization ID from organizations endpoint"""
        response = requests.get(f"{BASE_URL}/api/organizations/", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        orgs = response.json()
        if orgs and len(orgs) > 0:
            return orgs[0]["org_id"]
        return None
    
    def test_get_projects(self, auth_token, org_id):
        """Get projects for organization"""
        if not org_id:
            pytest.skip("No organization found for user")
        
        response = requests.get(f"{BASE_URL}/api/projects/?org_id={org_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get projects working - found {len(data)} projects")
        return data
    
    def test_get_single_project(self, auth_token, org_id):
        """Get a single project by ID"""
        if not org_id:
            pytest.skip("No organization found for user")
        
        # First get projects list
        projects_response = requests.get(f"{BASE_URL}/api/projects/?org_id={org_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        projects = projects_response.json()
        
        if not projects:
            pytest.skip("No projects found to test")
        
        project_id = projects[0]["project_id"]
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
        print(f"✓ Get single project working - project: {data.get('name', project_id)}")


class TestTasksAPI:
    """Test tasks API endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def project_id(self, auth_token):
        """Get a project ID for testing"""
        # Get user's org from organizations endpoint
        orgs_response = requests.get(f"{BASE_URL}/api/organizations/", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        orgs = orgs_response.json()
        if not orgs:
            return None
        
        org_id = orgs[0]["org_id"]
        
        # Get projects
        projects_response = requests.get(f"{BASE_URL}/api/projects/?org_id={org_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        projects = projects_response.json()
        
        if projects:
            return projects[0]["project_id"]
        return None
    
    def test_get_tasks_for_project(self, auth_token, project_id):
        """Get tasks for a project"""
        if not project_id:
            pytest.skip("No project found for testing")
        
        response = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get tasks working - found {len(data)} tasks")
    
    def test_get_single_task(self, auth_token, project_id):
        """Get a single task by ID"""
        if not project_id:
            pytest.skip("No project found for testing")
        
        # Get tasks list
        tasks_response = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        tasks = tasks_response.json()
        
        if not tasks:
            pytest.skip("No tasks found to test")
        
        task_id = tasks[0]["task_id"]
        response = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        print(f"✓ Get single task working - task: {data.get('title', task_id)}")


class TestOrganizationsAPI:
    """Test organizations API endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_organizations(self, auth_token):
        """Get user's organizations"""
        response = requests.get(f"{BASE_URL}/api/organizations/", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get organizations working - found {len(data)} organizations")


class TestRepositoryPattern:
    """Test that repository pattern is working correctly"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_project_repository_via_api(self, auth_token):
        """Verify project repository works via API"""
        # Get user's org from organizations endpoint
        orgs_response = requests.get(f"{BASE_URL}/api/organizations/", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        orgs = orgs_response.json()
        if not orgs:
            pytest.skip("No organization found")
        
        org_id = orgs[0]["org_id"]
        
        # Get projects - this uses project_repository
        response = requests.get(f"{BASE_URL}/api/projects/?org_id={org_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        
        # Verify response structure (no _id field from MongoDB)
        projects = response.json()
        for project in projects:
            assert "_id" not in project, "MongoDB _id should be excluded"
            assert "project_id" in project
        
        print(f"✓ Project repository working correctly - no _id leakage")
    
    def test_task_repository_via_api(self, auth_token):
        """Verify task repository works via API"""
        # Get user's org from organizations endpoint
        orgs_response = requests.get(f"{BASE_URL}/api/organizations/", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        orgs = orgs_response.json()
        if not orgs:
            pytest.skip("No organization found")
        
        org_id = orgs[0]["org_id"]
        
        # Get projects first
        projects_response = requests.get(f"{BASE_URL}/api/projects/?org_id={org_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        projects = projects_response.json()
        
        if not projects:
            pytest.skip("No projects found")
        
        project_id = projects[0]["project_id"]
        
        # Get tasks - this uses task_repository
        response = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        
        # Verify response structure (no _id field from MongoDB)
        tasks = response.json()
        for task in tasks:
            assert "_id" not in task, "MongoDB _id should be excluded"
            assert "task_id" in task
        
        print(f"✓ Task repository working correctly - no _id leakage")


class TestSettingsEndpoints:
    """Test settings-related endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def org_id(self, auth_token):
        """Get organization ID from organizations endpoint"""
        response = requests.get(f"{BASE_URL}/api/organizations/", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        orgs = response.json()
        if orgs and len(orgs) > 0:
            return orgs[0]["org_id"]
        return None
    
    def test_get_organization_details(self, auth_token, org_id):
        """Get organization details for settings"""
        if not org_id:
            pytest.skip("No organization found")
        
        response = requests.get(f"{BASE_URL}/api/organizations/{org_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "org_id" in data or "name" in data
        print(f"✓ Organization details endpoint working")
    
    def test_get_organization_members(self, auth_token, org_id):
        """Get organization members for team settings"""
        if not org_id:
            pytest.skip("No organization found")
        
        response = requests.get(f"{BASE_URL}/api/organizations/{org_id}/members", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Organization members endpoint working - found {len(data)} members")
    
    def test_get_roles(self, auth_token):
        """Get roles for role settings"""
        response = requests.get(f"{BASE_URL}/api/auth/roles", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        # API returns {"roles": [...]} structure
        if isinstance(data, dict) and "roles" in data:
            roles = data["roles"]
        else:
            roles = data
        assert isinstance(roles, list)
        print(f"✓ Roles endpoint working - found {len(roles)} roles")
    
    def test_get_branding(self, auth_token, org_id):
        """Get branding settings"""
        if not org_id:
            pytest.skip("No organization found")
        
        response = requests.get(f"{BASE_URL}/api/branding/{org_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        # Branding might not exist yet, so 200 or 404 are both acceptable
        assert response.status_code in [200, 404]
        print(f"✓ Branding endpoint accessible - status: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
