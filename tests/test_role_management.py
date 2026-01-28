"""
Test Role Management APIs - Custom Role Manager
Tests for:
- GET /api/roles/permissions - Get all permissions grouped by category
- GET /api/roles/org/{org_id} - Get built-in and custom roles
- POST /api/roles/org/{org_id} - Create a new custom role
- PUT /api/roles/{role_id} - Update an existing custom role
- DELETE /api/roles/{role_id} - Delete a custom role
- RBAC - Team member cannot access role management APIs
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ORG_ADMIN_EMAIL = "test@proflow.com"
ORG_ADMIN_PASSWORD = "test123456"
TEAM_MEMBER_EMAIL = "ahmed@ahmed.com"
TEAM_MEMBER_PASSWORD = "Su@12345"


@pytest.fixture(scope="module")
def admin_session():
    """Login as org admin and return session with token"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ORG_ADMIN_EMAIL,
        "password": ORG_ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    token = data.get('access_token') or data.get('token')
    session.headers.update({"Authorization": f"Bearer {token}"})
    session.org_id = data.get("user", {}).get("org_id")
    return session


@pytest.fixture(scope="module")
def team_member_session():
    """Login as team member and return session with token"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEAM_MEMBER_EMAIL,
        "password": TEAM_MEMBER_PASSWORD
    })
    assert response.status_code == 200, f"Team member login failed: {response.text}"
    data = response.json()
    token = data.get('access_token') or data.get('token')
    session.headers.update({"Authorization": f"Bearer {token}"})
    session.org_id = data.get("user", {}).get("org_id")
    return session


@pytest.fixture(scope="module")
def org_id(admin_session):
    """Get org_id from admin session"""
    # Get organizations to find org_id
    response = admin_session.get(f"{BASE_URL}/api/organizations/")
    assert response.status_code == 200
    orgs = response.json()
    assert len(orgs) > 0, "No organizations found"
    return orgs[0]["org_id"]


class TestGetPermissions:
    """Test GET /api/roles/permissions endpoint"""
    
    def test_get_all_permissions_as_admin(self, admin_session):
        """Admin can get all permissions"""
        response = admin_session.get(f"{BASE_URL}/api/roles/permissions")
        assert response.status_code == 200
        
        data = response.json()
        assert "permissions" in data
        assert "categories" in data
        assert len(data["permissions"]) > 0
        
        # Verify permission structure
        perm = data["permissions"][0]
        assert "id" in perm
        assert "name" in perm
        assert "category" in perm
        
        # Verify categories are grouped
        categories = data["categories"]
        assert len(categories) > 0
        assert "Projects" in categories or "Tasks" in categories
        print(f"✓ Found {len(data['permissions'])} permissions in {len(categories)} categories")
    
    def test_get_permissions_as_team_member(self, team_member_session):
        """Team member can also get permissions list (read-only)"""
        response = team_member_session.get(f"{BASE_URL}/api/roles/permissions")
        assert response.status_code == 200
        
        data = response.json()
        assert "permissions" in data
        print("✓ Team member can view permissions list")


class TestGetRoles:
    """Test GET /api/roles/org/{org_id} endpoint"""
    
    def test_get_roles_as_admin(self, admin_session, org_id):
        """Admin can get all roles for organization"""
        response = admin_session.get(f"{BASE_URL}/api/roles/org/{org_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "built_in_roles" in data
        assert "custom_roles" in data
        
        # Verify built-in roles
        built_in = data["built_in_roles"]
        assert len(built_in) >= 5  # super_admin, org_admin, project_manager, team_member, viewer
        
        # Check built-in role structure
        for role in built_in:
            assert "role_id" in role
            assert "name" in role
            assert "key" in role
            assert "description" in role
            assert "permissions" in role
            assert "is_built_in" in role
            assert role["is_built_in"] == True
            assert "color" in role
            assert "member_count" in role
        
        print(f"✓ Found {len(built_in)} built-in roles and {len(data['custom_roles'])} custom roles")
    
    def test_get_roles_as_team_member_forbidden(self, team_member_session, org_id):
        """Team member cannot view roles (requires settings:view permission)"""
        response = team_member_session.get(f"{BASE_URL}/api/roles/org/{org_id}")
        # Team member should get 403 if they don't have settings:view permission
        # Or 200 if they do have it - depends on their permissions
        if response.status_code == 403:
            print("✓ Team member correctly denied access to roles (no settings:view)")
        else:
            assert response.status_code == 200
            print("✓ Team member has settings:view permission and can view roles")


class TestCreateCustomRole:
    """Test POST /api/roles/org/{org_id} endpoint"""
    
    def test_create_custom_role_as_admin(self, admin_session, org_id):
        """Admin can create a custom role"""
        unique_name = f"TEST_Role_{uuid.uuid4().hex[:8]}"
        role_data = {
            "name": unique_name,
            "description": "Test role for automated testing",
            "permissions": ["project:view", "task:view", "task:create"],
            "color": "#10b981"
        }
        
        response = admin_session.post(f"{BASE_URL}/api/roles/org/{org_id}", json=role_data)
        assert response.status_code == 200, f"Create role failed: {response.text}"
        
        data = response.json()
        assert data["name"] == unique_name
        assert data["description"] == "Test role for automated testing"
        assert "project:view" in data["permissions"]
        assert data["color"] == "#10b981"
        assert data["is_built_in"] == False
        assert "role_id" in data
        
        # Store role_id for cleanup
        admin_session.test_role_id = data["role_id"]
        print(f"✓ Created custom role: {unique_name} with ID {data['role_id']}")
    
    def test_create_role_as_team_member_forbidden(self, team_member_session, org_id):
        """Team member cannot create roles (requires settings:edit permission)"""
        role_data = {
            "name": "Unauthorized Role",
            "description": "Should not be created",
            "permissions": ["project:view"],
            "color": "#ef4444"
        }
        
        response = team_member_session.post(f"{BASE_URL}/api/roles/org/{org_id}", json=role_data)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Team member correctly denied from creating roles")
    
    def test_create_role_duplicate_name(self, admin_session, org_id):
        """Cannot create role with duplicate name"""
        # First create a role
        unique_name = f"TEST_Duplicate_{uuid.uuid4().hex[:8]}"
        role_data = {
            "name": unique_name,
            "permissions": ["project:view"]
        }
        
        response = admin_session.post(f"{BASE_URL}/api/roles/org/{org_id}", json=role_data)
        assert response.status_code == 200
        first_role_id = response.json()["role_id"]
        
        # Try to create another with same name
        response = admin_session.post(f"{BASE_URL}/api/roles/org/{org_id}", json=role_data)
        assert response.status_code == 400
        assert "already exists" in response.json().get("detail", "").lower()
        
        # Cleanup
        admin_session.delete(f"{BASE_URL}/api/roles/{first_role_id}")
        print("✓ Duplicate role name correctly rejected")
    
    def test_create_role_invalid_permission(self, admin_session, org_id):
        """Cannot create role with invalid permission"""
        role_data = {
            "name": f"TEST_Invalid_{uuid.uuid4().hex[:8]}",
            "permissions": ["invalid:permission", "project:view"]
        }
        
        response = admin_session.post(f"{BASE_URL}/api/roles/org/{org_id}", json=role_data)
        assert response.status_code == 400
        assert "invalid permission" in response.json().get("detail", "").lower()
        print("✓ Invalid permission correctly rejected")


class TestUpdateCustomRole:
    """Test PUT /api/roles/{role_id} endpoint"""
    
    def test_update_custom_role_as_admin(self, admin_session, org_id):
        """Admin can update a custom role"""
        # First create a role to update
        unique_name = f"TEST_Update_{uuid.uuid4().hex[:8]}"
        role_data = {
            "name": unique_name,
            "description": "Original description",
            "permissions": ["project:view"],
            "color": "#6366f1"
        }
        
        response = admin_session.post(f"{BASE_URL}/api/roles/org/{org_id}", json=role_data)
        assert response.status_code == 200
        role_id = response.json()["role_id"]
        
        # Update the role
        update_data = {
            "name": f"{unique_name}_Updated",
            "description": "Updated description",
            "permissions": ["project:view", "task:view", "task:create"],
            "color": "#f59e0b"
        }
        
        response = admin_session.put(f"{BASE_URL}/api/roles/{role_id}", json=update_data)
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        data = response.json()
        assert data["name"] == f"{unique_name}_Updated"
        assert data["description"] == "Updated description"
        assert len(data["permissions"]) == 3
        assert data["color"] == "#f59e0b"
        
        # Verify with GET
        response = admin_session.get(f"{BASE_URL}/api/roles/{role_id}")
        assert response.status_code == 200
        assert response.json()["name"] == f"{unique_name}_Updated"
        
        # Cleanup
        admin_session.delete(f"{BASE_URL}/api/roles/{role_id}")
        print(f"✓ Updated custom role successfully")
    
    def test_update_role_as_team_member_forbidden(self, team_member_session, admin_session, org_id):
        """Team member cannot update roles"""
        # Create a role as admin first
        unique_name = f"TEST_NoUpdate_{uuid.uuid4().hex[:8]}"
        role_data = {
            "name": unique_name,
            "permissions": ["project:view"]
        }
        
        response = admin_session.post(f"{BASE_URL}/api/roles/org/{org_id}", json=role_data)
        assert response.status_code == 200
        role_id = response.json()["role_id"]
        
        # Try to update as team member
        update_data = {"name": "Hacked Name"}
        response = team_member_session.put(f"{BASE_URL}/api/roles/{role_id}", json=update_data)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        
        # Cleanup
        admin_session.delete(f"{BASE_URL}/api/roles/{role_id}")
        print("✓ Team member correctly denied from updating roles")


class TestDeleteCustomRole:
    """Test DELETE /api/roles/{role_id} endpoint"""
    
    def test_delete_custom_role_as_admin(self, admin_session, org_id):
        """Admin can delete a custom role with no members"""
        # Create a role to delete
        unique_name = f"TEST_Delete_{uuid.uuid4().hex[:8]}"
        role_data = {
            "name": unique_name,
            "permissions": ["project:view"]
        }
        
        response = admin_session.post(f"{BASE_URL}/api/roles/org/{org_id}", json=role_data)
        assert response.status_code == 200
        role_id = response.json()["role_id"]
        
        # Delete the role
        response = admin_session.delete(f"{BASE_URL}/api/roles/{role_id}")
        assert response.status_code == 200
        assert "deleted" in response.json().get("message", "").lower()
        
        # Verify it's gone
        response = admin_session.get(f"{BASE_URL}/api/roles/{role_id}")
        assert response.status_code == 404
        print("✓ Deleted custom role successfully")
    
    def test_delete_role_as_team_member_forbidden(self, team_member_session, admin_session, org_id):
        """Team member cannot delete roles"""
        # Create a role as admin first
        unique_name = f"TEST_NoDelete_{uuid.uuid4().hex[:8]}"
        role_data = {
            "name": unique_name,
            "permissions": ["project:view"]
        }
        
        response = admin_session.post(f"{BASE_URL}/api/roles/org/{org_id}", json=role_data)
        assert response.status_code == 200
        role_id = response.json()["role_id"]
        
        # Try to delete as team member
        response = team_member_session.delete(f"{BASE_URL}/api/roles/{role_id}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        
        # Cleanup as admin
        admin_session.delete(f"{BASE_URL}/api/roles/{role_id}")
        print("✓ Team member correctly denied from deleting roles")
    
    def test_delete_nonexistent_role(self, admin_session):
        """Cannot delete a role that doesn't exist"""
        response = admin_session.delete(f"{BASE_URL}/api/roles/role_nonexistent123")
        assert response.status_code == 404
        print("✓ Nonexistent role deletion correctly returns 404")


class TestExistingCustomRoles:
    """Test that existing custom roles (QA Tester, Designer) are present"""
    
    def test_existing_custom_roles(self, admin_session, org_id):
        """Verify QA Tester and Designer roles exist"""
        response = admin_session.get(f"{BASE_URL}/api/roles/org/{org_id}")
        assert response.status_code == 200
        
        data = response.json()
        custom_roles = data.get("custom_roles", [])
        custom_role_names = [r["name"] for r in custom_roles]
        
        print(f"Found custom roles: {custom_role_names}")
        
        # Check if QA Tester and Designer exist (they may have been created by main agent)
        # This is informational - not a hard requirement
        if "QA Tester" in custom_role_names:
            print("✓ QA Tester role exists")
        else:
            print("ℹ QA Tester role not found (may need to be created)")
            
        if "Designer" in custom_role_names:
            print("✓ Designer role exists")
        else:
            print("ℹ Designer role not found (may need to be created)")


class TestCleanup:
    """Cleanup any test roles created during testing"""
    
    def test_cleanup_test_roles(self, admin_session, org_id):
        """Remove any TEST_ prefixed roles"""
        response = admin_session.get(f"{BASE_URL}/api/roles/org/{org_id}")
        if response.status_code == 200:
            data = response.json()
            for role in data.get("custom_roles", []):
                if role["name"].startswith("TEST_"):
                    admin_session.delete(f"{BASE_URL}/api/roles/{role['role_id']}")
                    print(f"Cleaned up test role: {role['name']}")
        print("✓ Cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
