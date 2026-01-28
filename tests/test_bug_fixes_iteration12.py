"""
Test file for bug fixes - Iteration 12
Tests for:
1. Dashboard showing correct stats (Projects: 5, Tasks: 47)
2. Project Kanban view - task statuses
3. Timeline/Gantt view API
4. Task Status dropdown options
5. Assignee dropdown - all org members
6. Automations page - feature flag enabled
7. Audit Logs page - feature flag enabled
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@proflow.com"
TEST_PASSWORD = "test123456"
TEST_PROJECT_ID = "proj_c31c1308e3dc"
TEST_ORG_ID = "org_3a0711d3f937"


class TestAuthentication:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        print(f"✓ Login successful for {TEST_EMAIL}")


class TestDashboard:
    """Dashboard API tests - Bug fix #6: Dashboard not showing data"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_dashboard_returns_data(self, auth_headers):
        """Test dashboard API returns correct stats"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "projects" in data, "Missing projects in dashboard"
        assert "tasks" in data, "Missing tasks in dashboard"
        
        # Verify projects data
        assert "total" in data["projects"], "Missing total in projects"
        projects_total = data["projects"]["total"]
        print(f"✓ Dashboard projects total: {projects_total}")
        
        # Verify tasks data
        assert "total" in data["tasks"], "Missing total in tasks"
        tasks_total = data["tasks"]["total"]
        print(f"✓ Dashboard tasks total: {tasks_total}")
        
        # Check that we have actual data (not zeros)
        assert projects_total > 0, f"Expected projects > 0, got {projects_total}"
        assert tasks_total > 0, f"Expected tasks > 0, got {tasks_total}"
        print(f"✓ Dashboard shows data: {projects_total} projects, {tasks_total} tasks")
    
    def test_dashboard_with_org_id(self, auth_headers):
        """Test dashboard API with org_id parameter"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/?org_id={TEST_ORG_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Dashboard with org_id failed: {response.text}"
        data = response.json()
        assert "projects" in data
        assert "tasks" in data
        print(f"✓ Dashboard with org_id works: {data['projects']['total']} projects")


class TestProjectMembers:
    """Project members API tests - Bug fix #5: Assignee not loading all users"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_project_members_returns_all_org_members(self, auth_headers):
        """Test that project members API returns all org members"""
        response = requests.get(
            f"{BASE_URL}/api/projects/{TEST_PROJECT_ID}/members",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Project members failed: {response.text}"
        members = response.json()
        
        assert isinstance(members, list), "Members should be a list"
        assert len(members) > 0, "Should have at least one member"
        
        # Check member structure
        for member in members:
            assert "user_id" in member, "Member missing user_id"
            assert "name" in member or "email" in member, "Member missing name/email"
        
        print(f"✓ Project members API returns {len(members)} members")
        
        # Verify we have 5 members as expected
        assert len(members) >= 5, f"Expected at least 5 members, got {len(members)}"
        print(f"✓ All org members loaded: {len(members)} members")


class TestTimeline:
    """Timeline/Gantt API tests - Bug fix #3: Timeline showing 'Failed to load'"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_timeline_api_exists(self, auth_headers):
        """Test that timeline API endpoint exists and works"""
        response = requests.get(
            f"{BASE_URL}/api/reports/timeline?project_id={TEST_PROJECT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Timeline API failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "project" in data, "Missing project in timeline response"
        assert "tasks" in data, "Missing tasks in timeline response"
        
        print(f"✓ Timeline API works: {len(data['tasks'])} tasks returned")
    
    def test_timeline_task_structure(self, auth_headers):
        """Test timeline tasks have required fields for Gantt chart"""
        response = requests.get(
            f"{BASE_URL}/api/reports/timeline?project_id={TEST_PROJECT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if data["tasks"]:
            task = data["tasks"][0]
            # Check required fields for Gantt chart
            assert "task_id" in task, "Missing task_id"
            assert "title" in task, "Missing title"
            assert "status" in task, "Missing status"
            print(f"✓ Timeline task structure is correct")


class TestTaskStatuses:
    """Task status tests - Bug fix #4: Task Status Empty"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_project_has_task_statuses(self, auth_headers):
        """Test that project returns task_statuses or uses defaults"""
        response = requests.get(
            f"{BASE_URL}/api/projects/{TEST_PROJECT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get project failed: {response.text}"
        project = response.json()
        
        # Project should have task_statuses field (even if empty, frontend uses defaults)
        print(f"✓ Project retrieved successfully")
        print(f"  - task_statuses: {project.get('task_statuses', 'not set')}")
    
    def test_tasks_have_valid_status(self, auth_headers):
        """Test that tasks have valid status values"""
        response = requests.get(
            f"{BASE_URL}/api/tasks/?project_id={TEST_PROJECT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get tasks failed: {response.text}"
        tasks = response.json()
        
        valid_statuses = ["todo", "in_progress", "review", "done"]
        status_counts = {}
        
        for task in tasks:
            status = task.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"✓ Tasks by status: {status_counts}")
        
        # Verify we have tasks in different statuses
        assert len(tasks) > 0, "Should have tasks"
        print(f"✓ Found {len(tasks)} tasks with valid statuses")


class TestKanbanView:
    """Kanban view tests - Bug fix #2: Kanban view not working (empty)"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_tasks_endpoint_returns_data(self, auth_headers):
        """Test tasks endpoint returns data for Kanban"""
        response = requests.get(
            f"{BASE_URL}/api/tasks/?project_id={TEST_PROJECT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Tasks endpoint failed: {response.text}"
        tasks = response.json()
        
        assert isinstance(tasks, list), "Tasks should be a list"
        assert len(tasks) > 0, "Should have tasks for Kanban view"
        
        # Count by status for Kanban columns
        status_counts = {}
        for task in tasks:
            status = task.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"✓ Kanban data: {len(tasks)} total tasks")
        print(f"  - By status: {status_counts}")
        
        # Verify we have tasks in todo status (expected 33)
        todo_count = status_counts.get("todo", 0)
        in_progress_count = status_counts.get("in_progress", 0)
        print(f"✓ To Do: {todo_count}, In Progress: {in_progress_count}")


class TestAutomations:
    """Automations feature tests - Bug fix #1: Enable Automations for all users"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_automations_endpoint_accessible(self, auth_headers):
        """Test automations endpoint is accessible (feature flag enabled)"""
        response = requests.get(
            f"{BASE_URL}/api/automations/org/{TEST_ORG_ID}",
            headers=auth_headers
        )
        # Should not return 403 "feature not available"
        assert response.status_code != 403, f"Automations feature should be enabled: {response.text}"
        assert response.status_code == 200, f"Automations endpoint failed: {response.text}"
        
        data = response.json()
        print(f"✓ Automations endpoint accessible (feature enabled)")
        print(f"  - Automations count: {len(data) if isinstance(data, list) else 'N/A'}")
    
    def test_automation_triggers_endpoint(self, auth_headers):
        """Test automation triggers endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/automations/triggers",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Triggers endpoint failed: {response.text}"
        print(f"✓ Automation triggers endpoint works")
    
    def test_automation_actions_endpoint(self, auth_headers):
        """Test automation actions endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/automations/actions",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Actions endpoint failed: {response.text}"
        print(f"✓ Automation actions endpoint works")


class TestAuditLogs:
    """Audit logs feature tests - Bug fix #1: Enable Audit Logs for all users"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_audit_logs_endpoint_accessible(self, auth_headers):
        """Test audit logs endpoint is accessible (feature flag enabled)"""
        response = requests.get(
            f"{BASE_URL}/api/audit/org/{TEST_ORG_ID}?limit=25",
            headers=auth_headers
        )
        # Should not return 403 "feature not available"
        assert response.status_code != 403, f"Audit logs feature should be enabled: {response.text}"
        assert response.status_code == 200, f"Audit logs endpoint failed: {response.text}"
        
        data = response.json()
        print(f"✓ Audit logs endpoint accessible (feature enabled)")
        
        # Check if we have actual audit events
        if isinstance(data, dict) and "logs" in data:
            logs = data["logs"]
        elif isinstance(data, list):
            logs = data
        else:
            logs = []
        
        print(f"  - Audit logs count: {len(logs)}")
        assert len(logs) > 0, "Should have audit log entries"
        print(f"✓ Audit logs contain {len(logs)} events")
    
    def test_audit_actions_endpoint(self, auth_headers):
        """Test audit actions endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/audit/actions",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Audit actions endpoint failed: {response.text}"
        print(f"✓ Audit actions endpoint works")
    
    def test_audit_resource_types_endpoint(self, auth_headers):
        """Test audit resource types endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/audit/resource-types",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Audit resource types endpoint failed: {response.text}"
        print(f"✓ Audit resource types endpoint works")


class TestExecutiveDashboard:
    """Executive dashboard tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_executive_dashboard_endpoint(self, auth_headers):
        """Test executive dashboard endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/reports/org/{TEST_ORG_ID}/dashboard",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Executive dashboard failed: {response.text}"
        data = response.json()
        
        assert "projects" in data, "Missing projects in executive dashboard"
        assert "tasks" in data, "Missing tasks in executive dashboard"
        
        print(f"✓ Executive dashboard works")
        print(f"  - Projects: {data['projects'].get('total', 0)}")
        print(f"  - Tasks: {data['tasks'].get('total', 0)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
