"""
Test suite for refactored features:
1. Project Detail Page components (KanbanBoard, TaskListView, CreateTaskDialog, ProjectSettingsDialog)
2. Real-time Notification system
3. Email service for approval events
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Test credentials
ADMIN_EMAIL = "test@proflow.com"
ADMIN_PASSWORD = "test123456"
NON_ADMIN_EMAIL = "ahmed@ahmed.com"
NON_ADMIN_PASSWORD = "Su@12345"


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_admin_login(self):
        """Test admin user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        print(f"Admin login successful: {data['user'].get('email')}")
        return data["access_token"]
    
    def test_non_admin_login(self):
        """Test non-admin user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": NON_ADMIN_EMAIL,
            "password": NON_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"Non-admin login successful: {data['user'].get('email')}")
        return data["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Get admin headers"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def non_admin_token():
    """Get non-admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": NON_ADMIN_EMAIL,
        "password": NON_ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Non-admin authentication failed")


@pytest.fixture(scope="module")
def non_admin_headers(non_admin_token):
    """Get non-admin headers"""
    return {"Authorization": f"Bearer {non_admin_token}"}


class TestNotificationAPI:
    """Test notification endpoints"""
    
    def test_get_notifications(self, admin_headers):
        """Test getting notifications list"""
        response = requests.get(f"{BASE_URL}/api/notifications/", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get notifications: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Got {len(data)} notifications")
    
    def test_get_unread_count(self, admin_headers):
        """Test getting unread notification count"""
        response = requests.get(f"{BASE_URL}/api/notifications/unread-count", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get unread count: {response.text}"
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        print(f"Unread count: {data['count']}")
    
    def test_get_unread_only_notifications(self, admin_headers):
        """Test getting only unread notifications"""
        response = requests.get(f"{BASE_URL}/api/notifications/?unread_only=true", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get unread notifications: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        # All returned notifications should be unread
        for notif in data:
            assert notif.get("read") == False, "Found read notification in unread_only query"
        print(f"Got {len(data)} unread notifications")
    
    def test_mark_all_as_read(self, admin_headers):
        """Test marking all notifications as read"""
        response = requests.put(f"{BASE_URL}/api/notifications/read-all", headers=admin_headers)
        assert response.status_code == 200, f"Failed to mark all as read: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"Mark all as read response: {data['message']}")
        
        # Verify unread count is now 0
        count_response = requests.get(f"{BASE_URL}/api/notifications/unread-count", headers=admin_headers)
        assert count_response.status_code == 200
        assert count_response.json()["count"] == 0


class TestProjectsAPI:
    """Test project-related endpoints for refactored components"""
    
    def test_get_projects(self, admin_headers):
        """Test getting projects list"""
        response = requests.get(f"{BASE_URL}/api/projects/", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get projects: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Got {len(data)} projects")
        return data
    
    def test_get_project_detail(self, admin_headers):
        """Test getting project detail"""
        # First get projects list
        projects_response = requests.get(f"{BASE_URL}/api/projects/", headers=admin_headers)
        assert projects_response.status_code == 200
        projects = projects_response.json()
        
        if not projects:
            pytest.skip("No projects available for testing")
        
        project_id = projects[0]["project_id"]
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get project detail: {response.text}"
        data = response.json()
        assert "project_id" in data
        assert "name" in data
        print(f"Got project: {data['name']}")
        return data
    
    def test_get_project_members(self, admin_headers):
        """Test getting project members"""
        projects_response = requests.get(f"{BASE_URL}/api/projects/", headers=admin_headers)
        assert projects_response.status_code == 200
        projects = projects_response.json()
        
        if not projects:
            pytest.skip("No projects available for testing")
        
        project_id = projects[0]["project_id"]
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}/members", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get project members: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Got {len(data)} project members")


class TestTasksAPI:
    """Test task-related endpoints for KanbanBoard and TaskListView"""
    
    @pytest.fixture(scope="class")
    def project_id(self, admin_headers):
        """Get a project ID for testing"""
        response = requests.get(f"{BASE_URL}/api/projects/", headers=admin_headers)
        if response.status_code == 200 and response.json():
            return response.json()[0]["project_id"]
        pytest.skip("No projects available for testing")
    
    def test_get_tasks(self, admin_headers, project_id):
        """Test getting tasks list for a project"""
        response = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get tasks: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Got {len(data)} tasks for project {project_id}")
        return data
    
    def test_create_task(self, admin_headers, project_id):
        """Test creating a new task (CreateTaskDialog functionality)"""
        task_data = {
            "title": "TEST_Refactored_Task",
            "description": "Test task created for refactored components testing",
            "project_id": project_id,
            "status": "todo",
            "priority": "medium"
        }
        response = requests.post(f"{BASE_URL}/api/tasks/", json=task_data, headers=admin_headers)
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        data = response.json()
        assert "task_id" in data
        assert data["title"] == task_data["title"]
        print(f"Created task: {data['task_id']}")
        return data
    
    def test_update_task_status(self, admin_headers, project_id):
        """Test updating task status (KanbanBoard drag-drop functionality)"""
        # First create a task
        task_data = {
            "title": "TEST_Status_Update_Task",
            "project_id": project_id,
            "status": "todo",
            "priority": "low"
        }
        create_response = requests.post(f"{BASE_URL}/api/tasks/", json=task_data, headers=admin_headers)
        assert create_response.status_code in [200, 201]
        task = create_response.json()
        task_id = task["task_id"]
        
        # Update status to in_progress
        update_response = requests.put(f"{BASE_URL}/api/tasks/{task_id}", json={"status": "in_progress"}, headers=admin_headers)
        assert update_response.status_code == 200, f"Failed to update task status: {update_response.text}"
        updated_task = update_response.json()
        assert updated_task["status"] == "in_progress"
        print(f"Task status updated to: {updated_task['status']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=admin_headers)
    
    def test_delete_task(self, admin_headers, project_id):
        """Test deleting a task"""
        # First create a task
        task_data = {
            "title": "TEST_Delete_Task",
            "project_id": project_id,
            "status": "todo"
        }
        create_response = requests.post(f"{BASE_URL}/api/tasks/", json=task_data, headers=admin_headers)
        assert create_response.status_code in [200, 201]
        task_id = create_response.json()["task_id"]
        
        # Delete the task
        delete_response = requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=admin_headers)
        assert delete_response.status_code in [200, 204], f"Failed to delete task: {delete_response.text}"
        print(f"Task {task_id} deleted successfully")
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers=admin_headers)
        assert get_response.status_code == 404


class TestProjectSettings:
    """Test project settings endpoints (ProjectSettingsDialog functionality)"""
    
    @pytest.fixture(scope="class")
    def project_id(self, admin_headers):
        """Get a project ID for testing"""
        response = requests.get(f"{BASE_URL}/api/projects/", headers=admin_headers)
        if response.status_code == 200 and response.json():
            return response.json()[0]["project_id"]
        pytest.skip("No projects available for testing")
    
    def test_get_project_settings(self, admin_headers, project_id):
        """Test getting project settings including task_statuses"""
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get project: {response.text}"
        data = response.json()
        # Check if task_statuses exists (may be empty or default)
        print(f"Project has task_statuses: {'task_statuses' in data}")
        if "task_statuses" in data:
            print(f"Task statuses: {data['task_statuses']}")
    
    def test_update_project_statuses(self, admin_headers, project_id):
        """Test updating project task statuses"""
        new_statuses = [
            {"id": "todo", "label": "To Do", "color": "#64748b"},
            {"id": "in_progress", "label": "In Progress", "color": "#3b82f6"},
            {"id": "review", "label": "In Review", "color": "#a855f7"},
            {"id": "done", "label": "Done", "color": "#22c55e"}
        ]
        
        response = requests.put(
            f"{BASE_URL}/api/projects/{project_id}",
            json={"task_statuses": new_statuses},
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed to update project statuses: {response.text}"
        data = response.json()
        print(f"Updated project statuses successfully")


class TestEmailServiceMethods:
    """Test that email service methods exist and are callable"""
    
    def test_email_service_import(self):
        """Test that email service can be imported"""
        try:
            import sys
            sys.path.insert(0, '/app/backend')
            from services.email_service import email_service
            
            # Check that approval methods exist
            assert hasattr(email_service, 'send_approval_requested'), "Missing send_approval_requested method"
            assert hasattr(email_service, 'send_approval_approved'), "Missing send_approval_approved method"
            assert hasattr(email_service, 'send_approval_rejected'), "Missing send_approval_rejected method"
            
            print("Email service has all required approval methods")
        except ImportError as e:
            pytest.fail(f"Failed to import email service: {e}")


class TestApprovalWorkflowIntegration:
    """Test approval workflow with email notification integration"""
    
    def test_approval_service_has_email_integration(self):
        """Test that approval service imports and uses email service"""
        try:
            import sys
            sys.path.insert(0, '/app/backend')
            from services.approval_service import approval_service
            
            # Check that approval service has email-related methods
            assert hasattr(approval_service, '_notify_approvers'), "Missing _notify_approvers method"
            assert hasattr(approval_service, '_send_approval_result_email'), "Missing _send_approval_result_email method"
            
            print("Approval service has email integration methods")
        except ImportError as e:
            pytest.fail(f"Failed to import approval service: {e}")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_tasks(self, admin_headers):
        """Clean up any test tasks created during testing"""
        # Get all projects
        projects_response = requests.get(f"{BASE_URL}/api/projects/", headers=admin_headers)
        if projects_response.status_code != 200:
            return
        
        projects = projects_response.json()
        deleted_count = 0
        
        for project in projects:
            tasks_response = requests.get(
                f"{BASE_URL}/api/tasks/?project_id={project['project_id']}", 
                headers=admin_headers
            )
            if tasks_response.status_code == 200:
                tasks = tasks_response.json()
                for task in tasks:
                    if task.get("title", "").startswith("TEST_"):
                        delete_response = requests.delete(
                            f"{BASE_URL}/api/tasks/{task['task_id']}", 
                            headers=admin_headers
                        )
                        if delete_response.status_code in [200, 204]:
                            deleted_count += 1
        
        print(f"Cleaned up {deleted_count} test tasks")
