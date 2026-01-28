"""
Comprehensive API Endpoint Tests
Tests all major API endpoints for correct behavior, error handling, and permissions.
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "test@proflow.com"
SUPER_ADMIN_PASSWORD = "test123456"
TEAM_MEMBER_EMAIL = "ahmed@ahmed.com"
TEAM_MEMBER_PASSWORD = "Su@12345"


# =============================================
# Fixtures
# =============================================

@pytest.fixture(scope="module")
def super_admin_token():
    """Get super admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPER_ADMIN_EMAIL,
        "password": SUPER_ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Super admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def team_member_token():
    """Get team member auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEAM_MEMBER_EMAIL,
        "password": TEAM_MEMBER_PASSWORD
    })
    assert response.status_code == 200, f"Team member login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def org_id(super_admin_token):
    """Get organization ID"""
    response = requests.get(
        f"{BASE_URL}/api/organizations/",
        headers={"Authorization": f"Bearer {super_admin_token}"}
    )
    assert response.status_code == 200
    orgs = response.json()
    assert len(orgs) > 0, "No organizations found"
    return orgs[0]["org_id"]


@pytest.fixture(scope="module")
def project_id(super_admin_token, org_id):
    """Get or create a test project"""
    # List existing projects
    response = requests.get(
        f"{BASE_URL}/api/projects/",
        headers={"Authorization": f"Bearer {super_admin_token}"}
    )
    assert response.status_code == 200
    projects = response.json()
    
    if projects:
        return projects[0]["project_id"]
    
    # Create a new project if none exist
    response = requests.post(
        f"{BASE_URL}/api/projects/",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={
            "name": "Test Project",
            "description": "Project for API tests",
            "org_id": org_id
        }
    )
    assert response.status_code in [200, 201]
    return response.json()["project_id"]


# =============================================
# Auth API Tests
# =============================================

class TestAuthAPI:
    """Test authentication endpoints"""
    
    def test_login_success(self):
        """Test successful login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == SUPER_ADMIN_EMAIL
    
    def test_login_invalid_password(self):
        """Test login with invalid password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
    
    def test_login_invalid_email(self):
        """Test login with non-existent email"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "anypassword"
        })
        assert response.status_code == 401
    
    def test_me_endpoint(self, super_admin_token):
        """Test /me endpoint returns current user"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == SUPER_ADMIN_EMAIL
    
    def test_me_without_token(self):
        """Test /me endpoint without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403]


# =============================================
# Organization API Tests
# =============================================

class TestOrganizationAPI:
    """Test organization endpoints"""
    
    def test_list_organizations(self, super_admin_token):
        """Test listing user's organizations"""
        response = requests.get(
            f"{BASE_URL}/api/organizations/",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        orgs = response.json()
        assert isinstance(orgs, list)
        assert len(orgs) > 0
    
    def test_get_organization(self, super_admin_token, org_id):
        """Test getting organization details"""
        response = requests.get(
            f"{BASE_URL}/api/organizations/{org_id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["org_id"] == org_id
        assert "name" in data
    
    def test_get_organization_members(self, super_admin_token, org_id):
        """Test getting organization members"""
        response = requests.get(
            f"{BASE_URL}/api/organizations/{org_id}/members",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        members = response.json()
        assert isinstance(members, list)
        assert len(members) > 0
        # Check member structure
        member = members[0]
        assert "user_id" in member
        assert "org_role" in member
    
    def test_unauthorized_access(self, org_id):
        """Test access without token"""
        response = requests.get(f"{BASE_URL}/api/organizations/{org_id}")
        assert response.status_code in [401, 403]


# =============================================
# Project API Tests
# =============================================

class TestProjectAPI:
    """Test project endpoints"""
    
    def test_list_projects(self, super_admin_token):
        """Test listing projects"""
        response = requests.get(
            f"{BASE_URL}/api/projects/",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        projects = response.json()
        assert isinstance(projects, list)
    
    def test_get_project(self, super_admin_token, project_id):
        """Test getting project details"""
        response = requests.get(
            f"{BASE_URL}/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
        assert "name" in data
    
    def test_update_project(self, super_admin_token, project_id):
        """Test updating project"""
        new_description = f"Updated at {datetime.now().isoformat()}"
        response = requests.put(
            f"{BASE_URL}/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={"description": new_description}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == new_description
    
    def test_get_nonexistent_project(self, super_admin_token):
        """Test getting non-existent project"""
        response = requests.get(
            f"{BASE_URL}/api/projects/nonexistent_id",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 404


# =============================================
# Task API Tests
# =============================================

class TestTaskAPI:
    """Test task endpoints"""
    
    @pytest.fixture
    def created_task(self, super_admin_token, project_id):
        """Create a task for testing"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "project_id": project_id,
                "title": f"Test Task {uuid.uuid4().hex[:8]}",
                "description": "Task for API testing",
                "status": "todo",
                "priority": "medium"
            }
        )
        assert response.status_code in [200, 201]
        return response.json()
    
    def test_list_tasks(self, super_admin_token):
        """Test listing tasks"""
        response = requests.get(
            f"{BASE_URL}/api/tasks/",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        tasks = response.json()
        assert isinstance(tasks, list)
    
    def test_list_tasks_by_project(self, super_admin_token, project_id):
        """Test listing tasks filtered by project"""
        response = requests.get(
            f"{BASE_URL}/api/tasks/?project_id={project_id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        tasks = response.json()
        assert isinstance(tasks, list)
        for task in tasks:
            assert task["project_id"] == project_id
    
    def test_create_task(self, super_admin_token, project_id):
        """Test creating a task"""
        task_title = f"New Task {uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "project_id": project_id,
                "title": task_title,
                "description": "Test task creation",
                "status": "todo",
                "priority": "high"
            }
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["title"] == task_title
        assert data["status"] == "todo"
        assert data["priority"] == "high"
        return data["task_id"]
    
    def test_get_task(self, super_admin_token, created_task):
        """Test getting task details"""
        response = requests.get(
            f"{BASE_URL}/api/tasks/{created_task['task_id']}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == created_task["task_id"]
    
    def test_update_task(self, super_admin_token, created_task):
        """Test updating task"""
        response = requests.put(
            f"{BASE_URL}/api/tasks/{created_task['task_id']}",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={"priority": "low", "description": "Updated description"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "low"
    
    def test_delete_task(self, super_admin_token, created_task):
        """Test deleting task"""
        response = requests.delete(
            f"{BASE_URL}/api/tasks/{created_task['task_id']}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        
        # Verify deleted
        response = requests.get(
            f"{BASE_URL}/api/tasks/{created_task['task_id']}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 404


# =============================================
# Role API Tests
# =============================================

class TestRoleAPI:
    """Test role management endpoints"""
    
    def test_get_permissions(self, super_admin_token):
        """Test getting all permissions"""
        response = requests.get(
            f"{BASE_URL}/api/roles/permissions",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "permissions" in data
        assert "categories" in data
        assert len(data["permissions"]) > 0
    
    def test_get_roles(self, super_admin_token, org_id):
        """Test getting organization roles"""
        response = requests.get(
            f"{BASE_URL}/api/roles/org/{org_id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "built_in_roles" in data
        assert "custom_roles" in data
        assert len(data["built_in_roles"]) == 5  # super_admin, org_admin, project_manager, team_member, viewer
    
    def test_create_custom_role(self, super_admin_token, org_id):
        """Test creating a custom role"""
        role_name = f"Test Role {uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/roles/org/{org_id}",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "name": role_name,
                "description": "Test custom role",
                "permissions": ["project:view", "task:view", "task:create"]
            }
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == role_name
        assert len(data["permissions"]) == 3
        return data["role_id"]
    
    def test_create_role_with_invalid_permission(self, super_admin_token, org_id):
        """Test creating role with invalid permission fails"""
        response = requests.post(
            f"{BASE_URL}/api/roles/org/{org_id}",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "name": "Invalid Role",
                "permissions": ["invalid:permission"]
            }
        )
        assert response.status_code == 400


# =============================================
# Time Tracking API Tests
# =============================================

class TestTimeTrackingAPI:
    """Test time tracking endpoints"""
    
    def test_get_active_timer(self, super_admin_token):
        """Test getting active timer status"""
        response = requests.get(
            f"{BASE_URL}/api/time-entries/timer/active",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "active" in data
    
    def test_get_time_entries(self, super_admin_token):
        """Test getting time entries"""
        response = requests.get(
            f"{BASE_URL}/api/time-entries/",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        entries = response.json()
        assert isinstance(entries, list)
    
    def test_create_time_entry(self, super_admin_token, project_id):
        """Test creating manual time entry"""
        # First get a task
        tasks_response = requests.get(
            f"{BASE_URL}/api/tasks/?project_id={project_id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        if tasks_response.status_code == 200 and tasks_response.json():
            task_id = tasks_response.json()[0]["task_id"]
            
            response = requests.post(
                f"{BASE_URL}/api/time-entries/",
                headers={"Authorization": f"Bearer {super_admin_token}"},
                json={
                    "task_id": task_id,
                    "duration_minutes": 60,
                    "description": "Test time entry"
                }
            )
            assert response.status_code in [200, 201]
            data = response.json()
            assert data["duration_minutes"] == 60
    
    def test_get_time_summary(self, super_admin_token):
        """Test getting time summary"""
        response = requests.get(
            f"{BASE_URL}/api/time-entries/summary",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_hours" in data


# =============================================
# Automation API Tests
# =============================================

class TestAutomationAPI:
    """Test automation endpoints"""
    
    def test_get_trigger_types(self, super_admin_token):
        """Test getting automation trigger types"""
        response = requests.get(
            f"{BASE_URL}/api/automations/triggers",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "triggers" in data
        assert len(data["triggers"]) > 0
    
    def test_get_action_types(self, super_admin_token):
        """Test getting automation action types"""
        response = requests.get(
            f"{BASE_URL}/api/automations/actions",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "actions" in data
        assert len(data["actions"]) > 0
    
    def test_get_automations(self, super_admin_token, org_id):
        """Test getting organization automations"""
        response = requests.get(
            f"{BASE_URL}/api/automations/org/{org_id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "automations" in data


# =============================================
# Branding API Tests
# =============================================

class TestBrandingAPI:
    """Test branding endpoints"""
    
    def test_get_branding(self, super_admin_token, org_id):
        """Test getting organization branding"""
        response = requests.get(
            f"{BASE_URL}/api/branding/org/{org_id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "primary_color" in data
        assert "secondary_color" in data
    
    def test_get_preset_fonts(self, super_admin_token):
        """Test getting preset fonts"""
        response = requests.get(
            f"{BASE_URL}/api/branding/fonts",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "fonts" in data
    
    def test_get_preset_themes(self, super_admin_token):
        """Test getting preset themes"""
        response = requests.get(
            f"{BASE_URL}/api/branding/themes",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "themes" in data
    
    def test_update_branding(self, super_admin_token, org_id):
        """Test updating branding"""
        response = requests.put(
            f"{BASE_URL}/api/branding/org/{org_id}",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={"primary_color": "#1a1a2e"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["primary_color"] == "#1a1a2e"


# =============================================
# Notification API Tests
# =============================================

class TestNotificationAPI:
    """Test notification endpoints"""
    
    def test_get_notifications(self, super_admin_token):
        """Test getting user notifications"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_unread_count(self, super_admin_token):
        """Test getting unread notification count"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/unread-count",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data


# =============================================
# Run tests
# =============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
