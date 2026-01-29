"""
RBAC Permission Tests - Iteration 13
Tests Role-Based Access Control across the application
- Team member restrictions (cannot delete tasks/projects, create automations, etc.)
- Org admin full access
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://docflows.preview.emergentagent.com')

# Test credentials
ORG_ADMIN_EMAIL = "test@proflow.com"
ORG_ADMIN_PASSWORD = "test123456"
TEAM_MEMBER_EMAIL = "ahmed@ahmed.com"
TEAM_MEMBER_PASSWORD = "Su@12345"


class TestRBACSetup:
    """Setup and verify test accounts"""
    
    @pytest.fixture(scope="class")
    def org_admin_token(self):
        """Get org admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ORG_ADMIN_EMAIL,
            "password": ORG_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Org admin login failed: {response.text}"
        data = response.json()
        return data.get("access_token")
    
    @pytest.fixture(scope="class")
    def team_member_token(self):
        """Get team member auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEAM_MEMBER_EMAIL,
            "password": TEAM_MEMBER_PASSWORD
        })
        assert response.status_code == 200, f"Team member login failed: {response.text}"
        data = response.json()
        return data.get("access_token")
    
    @pytest.fixture(scope="class")
    def org_id(self, org_admin_token):
        """Get organization ID"""
        response = requests.get(f"{BASE_URL}/api/organizations/", headers={
            "Authorization": f"Bearer {org_admin_token}"
        })
        assert response.status_code == 200
        orgs = response.json()
        assert len(orgs) > 0, "No organizations found"
        return orgs[0]["org_id"]
    
    def test_org_admin_permissions(self, org_admin_token, org_id):
        """Verify org admin has full permissions"""
        response = requests.get(f"{BASE_URL}/api/auth/permissions/{org_id}", headers={
            "Authorization": f"Bearer {org_admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Org admin should have these permissions
        expected_permissions = [
            "project:create", "project:delete", "task:delete",
            "automation:create", "customer:create", "member:invite"
        ]
        for perm in expected_permissions:
            assert perm in data["permissions"], f"Org admin missing permission: {perm}"
        
        print(f"Org admin role: {data['role']}, permissions count: {len(data['permissions'])}")
    
    def test_team_member_permissions(self, team_member_token, org_id):
        """Verify team member has limited permissions"""
        response = requests.get(f"{BASE_URL}/api/auth/permissions/{org_id}", headers={
            "Authorization": f"Bearer {team_member_token}"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Team member should NOT have these permissions
        restricted_permissions = [
            "project:create", "project:delete", "task:delete",
            "automation:create", "customer:create", "member:invite"
        ]
        for perm in restricted_permissions:
            assert perm not in data["permissions"], f"Team member should NOT have: {perm}"
        
        # Team member SHOULD have these permissions
        allowed_permissions = [
            "task:view", "task:create", "task:change_status",
            "comment:view", "comment:create", "project:view"
        ]
        for perm in allowed_permissions:
            assert perm in data["permissions"], f"Team member missing permission: {perm}"
        
        print(f"Team member role: {data['role']}, permissions count: {len(data['permissions'])}")


class TestTaskRBAC:
    """Test RBAC on task operations"""
    
    @pytest.fixture(scope="class")
    def org_admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ORG_ADMIN_EMAIL,
            "password": ORG_ADMIN_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def team_member_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEAM_MEMBER_EMAIL,
            "password": TEAM_MEMBER_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def project_id(self, org_admin_token):
        """Get a project ID for testing"""
        response = requests.get(f"{BASE_URL}/api/projects/", headers={
            "Authorization": f"Bearer {org_admin_token}"
        })
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) > 0, "No projects found"
        return projects[0]["project_id"]
    
    @pytest.fixture(scope="class")
    def test_task_id(self, org_admin_token, project_id):
        """Create a test task for RBAC testing"""
        response = requests.post(f"{BASE_URL}/api/tasks/", headers={
            "Authorization": f"Bearer {org_admin_token}",
            "Content-Type": "application/json"
        }, json={
            "project_id": project_id,
            "title": "TEST_RBAC_Task_For_Deletion",
            "description": "Test task for RBAC testing",
            "status": "todo",
            "priority": "medium",
            "assignee_ids": []
        })
        assert response.status_code == 200, f"Failed to create test task: {response.text}"
        return response.json()["task_id"]
    
    def test_team_member_can_view_tasks(self, team_member_token, project_id):
        """Team member should be able to view tasks"""
        response = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers={
            "Authorization": f"Bearer {team_member_token}"
        })
        assert response.status_code == 200, f"Team member cannot view tasks: {response.text}"
        print(f"Team member can view {len(response.json())} tasks")
    
    def test_team_member_can_create_task(self, team_member_token, project_id):
        """Team member should be able to create tasks"""
        response = requests.post(f"{BASE_URL}/api/tasks/", headers={
            "Authorization": f"Bearer {team_member_token}",
            "Content-Type": "application/json"
        }, json={
            "project_id": project_id,
            "title": "TEST_Team_Member_Task",
            "description": "Created by team member",
            "status": "todo",
            "priority": "low",
            "assignee_ids": []
        })
        assert response.status_code == 200, f"Team member cannot create task: {response.text}"
        task_id = response.json()["task_id"]
        print(f"Team member created task: {task_id}")
        
        # Cleanup - delete with admin
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ORG_ADMIN_EMAIL,
            "password": ORG_ADMIN_PASSWORD
        })
        admin_token = admin_response.json().get("access_token")
        requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
    
    def test_team_member_cannot_delete_task(self, team_member_token, test_task_id):
        """Team member should NOT be able to delete tasks - expect 403"""
        response = requests.delete(f"{BASE_URL}/api/tasks/{test_task_id}", headers={
            "Authorization": f"Bearer {team_member_token}"
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        assert "Permission denied" in response.json().get("detail", ""), "Expected permission denied message"
        print(f"Team member correctly denied task deletion: {response.json()}")
    
    def test_org_admin_can_delete_task(self, org_admin_token, test_task_id):
        """Org admin should be able to delete tasks"""
        response = requests.delete(f"{BASE_URL}/api/tasks/{test_task_id}", headers={
            "Authorization": f"Bearer {org_admin_token}"
        })
        assert response.status_code == 200, f"Org admin cannot delete task: {response.text}"
        print("Org admin successfully deleted task")


class TestProjectRBAC:
    """Test RBAC on project operations"""
    
    @pytest.fixture(scope="class")
    def org_admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ORG_ADMIN_EMAIL,
            "password": ORG_ADMIN_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def team_member_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEAM_MEMBER_EMAIL,
            "password": TEAM_MEMBER_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def org_id(self, org_admin_token):
        response = requests.get(f"{BASE_URL}/api/organizations/", headers={
            "Authorization": f"Bearer {org_admin_token}"
        })
        return response.json()[0]["org_id"]
    
    def test_team_member_can_view_projects(self, team_member_token, org_id):
        """Team member should be able to view projects"""
        response = requests.get(f"{BASE_URL}/api/projects/?org_id={org_id}", headers={
            "Authorization": f"Bearer {team_member_token}"
        })
        assert response.status_code == 200, f"Team member cannot view projects: {response.text}"
        print(f"Team member can view {len(response.json())} projects")
    
    def test_team_member_cannot_create_project(self, team_member_token, org_id):
        """Team member should NOT be able to create projects - expect 403"""
        response = requests.post(f"{BASE_URL}/api/projects/?org_id={org_id}", headers={
            "Authorization": f"Bearer {team_member_token}",
            "Content-Type": "application/json"
        }, json={
            "name": "TEST_Unauthorized_Project",
            "description": "Should not be created",
            "status": "active"
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"Team member correctly denied project creation: {response.json()}")
    
    def test_team_member_cannot_delete_project(self, team_member_token, org_admin_token, org_id):
        """Team member should NOT be able to delete projects - expect 403"""
        # First create a project with admin
        create_response = requests.post(f"{BASE_URL}/api/projects/?org_id={org_id}", headers={
            "Authorization": f"Bearer {org_admin_token}",
            "Content-Type": "application/json"
        }, json={
            "name": "TEST_RBAC_Project_For_Deletion",
            "description": "Test project for RBAC testing",
            "status": "active"
        })
        assert create_response.status_code == 200, f"Failed to create test project: {create_response.text}"
        project_id = create_response.json()["project_id"]
        
        # Try to delete with team member
        response = requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers={
            "Authorization": f"Bearer {team_member_token}"
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"Team member correctly denied project deletion: {response.json()}")
        
        # Cleanup - delete with admin
        requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers={
            "Authorization": f"Bearer {org_admin_token}"
        })
    
    def test_org_admin_can_create_project(self, org_admin_token, org_id):
        """Org admin should be able to create projects"""
        response = requests.post(f"{BASE_URL}/api/projects/?org_id={org_id}", headers={
            "Authorization": f"Bearer {org_admin_token}",
            "Content-Type": "application/json"
        }, json={
            "name": "TEST_Admin_Project",
            "description": "Created by admin",
            "status": "active"
        })
        assert response.status_code == 200, f"Org admin cannot create project: {response.text}"
        project_id = response.json()["project_id"]
        print(f"Org admin created project: {project_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers={
            "Authorization": f"Bearer {org_admin_token}"
        })


class TestAutomationRBAC:
    """Test RBAC on automation operations"""
    
    @pytest.fixture(scope="class")
    def org_admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ORG_ADMIN_EMAIL,
            "password": ORG_ADMIN_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def team_member_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEAM_MEMBER_EMAIL,
            "password": TEAM_MEMBER_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def org_id(self, org_admin_token):
        response = requests.get(f"{BASE_URL}/api/organizations/", headers={
            "Authorization": f"Bearer {org_admin_token}"
        })
        return response.json()[0]["org_id"]
    
    def test_team_member_cannot_create_automation(self, team_member_token, org_id):
        """Team member should NOT be able to create automations - expect 403"""
        response = requests.post(f"{BASE_URL}/api/automations/org/{org_id}", headers={
            "Authorization": f"Bearer {team_member_token}",
            "Content-Type": "application/json"
        }, json={
            "name": "TEST_Unauthorized_Automation",
            "trigger": {"type": "task_created", "conditions": {}},
            "actions": [{"type": "notify_users", "config": {}}],
            "enabled": True
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"Team member correctly denied automation creation: {response.json()}")
    
    def test_org_admin_can_create_automation(self, org_admin_token, org_id):
        """Org admin should be able to create automations"""
        response = requests.post(f"{BASE_URL}/api/automations/org/{org_id}", headers={
            "Authorization": f"Bearer {org_admin_token}",
            "Content-Type": "application/json"
        }, json={
            "name": "TEST_Admin_Automation",
            "trigger": {"type": "task_created", "conditions": {}},
            "actions": [{"type": "notify_users", "config": {"user_ids": [], "title": "Test", "message": "Test"}}],
            "enabled": False
        })
        assert response.status_code == 200, f"Org admin cannot create automation: {response.text}"
        automation_id = response.json()["automation_id"]
        print(f"Org admin created automation: {automation_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/automations/{automation_id}", headers={
            "Authorization": f"Bearer {org_admin_token}"
        })


class TestCustomerRBAC:
    """Test RBAC on customer operations"""
    
    @pytest.fixture(scope="class")
    def org_admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ORG_ADMIN_EMAIL,
            "password": ORG_ADMIN_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def team_member_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEAM_MEMBER_EMAIL,
            "password": TEAM_MEMBER_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def org_id(self, org_admin_token):
        response = requests.get(f"{BASE_URL}/api/organizations/", headers={
            "Authorization": f"Bearer {org_admin_token}"
        })
        return response.json()[0]["org_id"]
    
    def test_team_member_can_view_customers(self, team_member_token, org_id):
        """Team member should be able to view customers"""
        response = requests.get(f"{BASE_URL}/api/customers/?org_id={org_id}", headers={
            "Authorization": f"Bearer {team_member_token}"
        })
        assert response.status_code == 200, f"Team member cannot view customers: {response.text}"
        print(f"Team member can view {len(response.json())} customers")
    
    def test_team_member_cannot_create_customer(self, team_member_token, org_id):
        """Team member should NOT be able to create customers - expect 403"""
        response = requests.post(f"{BASE_URL}/api/customers/?org_id={org_id}", headers={
            "Authorization": f"Bearer {team_member_token}",
            "Content-Type": "application/json"
        }, json={
            "name": "TEST_Unauthorized_Customer",
            "email": "test@test.com"
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"Team member correctly denied customer creation: {response.json()}")


class TestCommentRBAC:
    """Test RBAC on comment operations"""
    
    @pytest.fixture(scope="class")
    def org_admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ORG_ADMIN_EMAIL,
            "password": ORG_ADMIN_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def team_member_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEAM_MEMBER_EMAIL,
            "password": TEAM_MEMBER_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def task_id(self, org_admin_token):
        """Get a task ID for testing"""
        response = requests.get(f"{BASE_URL}/api/tasks/", headers={
            "Authorization": f"Bearer {org_admin_token}"
        })
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) > 0, "No tasks found"
        return tasks[0]["task_id"]
    
    def test_team_member_can_create_comment(self, team_member_token, task_id):
        """Team member should be able to create comments (they have comment:create)"""
        response = requests.post(f"{BASE_URL}/api/comments/", headers={
            "Authorization": f"Bearer {team_member_token}",
            "Content-Type": "application/json"
        }, json={
            "task_id": task_id,
            "content": "TEST_Team_Member_Comment - This is a test comment"
        })
        assert response.status_code == 200, f"Team member cannot create comment: {response.text}"
        comment_id = response.json()["comment_id"]
        print(f"Team member created comment: {comment_id}")
        
        # Cleanup - team member can delete their own comment
        requests.delete(f"{BASE_URL}/api/comments/{comment_id}", headers={
            "Authorization": f"Bearer {team_member_token}"
        })
    
    def test_team_member_can_view_comments(self, team_member_token, task_id):
        """Team member should be able to view comments"""
        response = requests.get(f"{BASE_URL}/api/comments/?task_id={task_id}", headers={
            "Authorization": f"Bearer {team_member_token}"
        })
        assert response.status_code == 200, f"Team member cannot view comments: {response.text}"
        print(f"Team member can view {len(response.json())} comments")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
