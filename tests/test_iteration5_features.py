"""
Backend API Tests for Iteration 5 Features:
- Assignee dropdown from project members (GET /api/projects/{id}/members)
- Custom task statuses per project (PUT /api/projects/{id} with task_statuses)
- Task activity log (GET /api/tasks/{id}/activity)
- Task assignee_ids field for multi-select
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://costmanager-5.preview.emergentagent.com')

# Generate unique test user for each test run
UNIQUE_ID = uuid.uuid4().hex[:8]
TEST_USER = {
    "email": f"test_iter5_{UNIQUE_ID}@example.com",
    "password": "TestPass123!",
    "name": f"Test Iter5 User {UNIQUE_ID}"
}


@pytest.fixture(scope="module")
def session():
    return requests.Session()


@pytest.fixture(scope="module")
def auth_data(session):
    """Register user and get auth token"""
    response = session.post(f"{BASE_URL}/api/auth/register", json=TEST_USER)
    if response.status_code == 200:
        data = response.json()
        return {
            "token": data["access_token"],
            "user": data["user"]
        }
    elif response.status_code == 400 and "already registered" in response.text:
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        data = login_response.json()
        return {
            "token": data["access_token"],
            "user": data["user"]
        }
    else:
        pytest.fail(f"Registration failed: {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_data):
    return {
        "Authorization": f"Bearer {auth_data['token']}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def org_id(session, auth_headers):
    """Get or create organization"""
    response = session.get(f"{BASE_URL}/api/organizations/", headers=auth_headers)
    assert response.status_code == 200
    orgs = response.json()
    if orgs:
        return orgs[0]["org_id"]
    
    response = session.post(f"{BASE_URL}/api/organizations/", 
                           headers=auth_headers,
                           json={"name": f"Test Org Iter5 {UNIQUE_ID}"})
    assert response.status_code == 200
    return response.json()["org_id"]


@pytest.fixture(scope="module")
def project_id(session, auth_headers, org_id):
    """Create a test project with custom statuses"""
    custom_statuses = [
        {"id": "backlog", "label": "Backlog", "color": "#6b7280"},
        {"id": "todo", "label": "To Do", "color": "#64748b"},
        {"id": "in_progress", "label": "In Progress", "color": "#3b82f6"},
        {"id": "testing", "label": "Testing", "color": "#f59e0b"},
        {"id": "done", "label": "Done", "color": "#22c55e"}
    ]
    
    response = session.post(f"{BASE_URL}/api/projects/?org_id={org_id}",
                           headers=auth_headers,
                           json={
                               "name": f"CustomStatusProject_{UNIQUE_ID}",
                               "description": "Project for testing custom statuses and assignees",
                               "status": "active",
                               "task_statuses": custom_statuses
                           })
    assert response.status_code == 200, f"Project creation failed: {response.text}"
    return response.json()["project_id"]


@pytest.fixture(scope="module")
def task_id(session, auth_headers, project_id, auth_data):
    """Create a test task with assignee"""
    response = session.post(f"{BASE_URL}/api/tasks/",
                           headers=auth_headers,
                           json={
                               "title": f"AssigneeTestTask_{UNIQUE_ID}",
                               "description": "Task for testing assignees and activity",
                               "project_id": project_id,
                               "status": "todo",
                               "priority": "high",
                               "assignee_ids": [auth_data["user"]["user_id"]]
                           })
    assert response.status_code == 200, f"Task creation failed: {response.text}"
    return response.json()["task_id"]


class TestProjectMembers:
    """Test GET /api/projects/{id}/members endpoint"""
    
    def test_get_project_members_requires_auth(self, session, project_id):
        """Project members endpoint should require authentication"""
        response = session.get(f"{BASE_URL}/api/projects/{project_id}/members")
        assert response.status_code == 401
    
    def test_get_project_members_success(self, session, auth_headers, project_id):
        """Should return list of project members"""
        response = session.get(f"{BASE_URL}/api/projects/{project_id}/members", headers=auth_headers)
        assert response.status_code == 200
        
        members = response.json()
        assert isinstance(members, list)
        assert len(members) >= 1, "Project should have at least one member (creator)"
        
        # Verify member structure
        member = members[0]
        assert "user_id" in member
        assert "name" in member
        assert "email" in member
    
    def test_project_members_includes_creator(self, session, auth_headers, project_id, auth_data):
        """Project members should include the project creator"""
        response = session.get(f"{BASE_URL}/api/projects/{project_id}/members", headers=auth_headers)
        assert response.status_code == 200
        
        members = response.json()
        user_ids = [m["user_id"] for m in members]
        assert auth_data["user"]["user_id"] in user_ids, "Creator should be in project members"
    
    def test_project_members_not_found(self, session, auth_headers):
        """Should return 404 for non-existent project"""
        response = session.get(f"{BASE_URL}/api/projects/nonexistent_project/members", headers=auth_headers)
        assert response.status_code == 404


class TestCustomTaskStatuses:
    """Test custom task statuses per project"""
    
    def test_project_has_custom_statuses(self, session, auth_headers, project_id):
        """Project should have custom task_statuses"""
        response = session.get(f"{BASE_URL}/api/projects/{project_id}", headers=auth_headers)
        assert response.status_code == 200
        
        project = response.json()
        assert "task_statuses" in project
        assert isinstance(project["task_statuses"], list)
        assert len(project["task_statuses"]) >= 4, "Should have custom statuses"
        
        # Verify status structure
        status = project["task_statuses"][0]
        assert "id" in status
        assert "label" in status
        assert "color" in status
    
    def test_update_project_statuses(self, session, auth_headers, project_id):
        """Should be able to update project task_statuses"""
        new_statuses = [
            {"id": "new", "label": "New", "color": "#9ca3af"},
            {"id": "active", "label": "Active", "color": "#3b82f6"},
            {"id": "blocked", "label": "Blocked", "color": "#ef4444"},
            {"id": "completed", "label": "Completed", "color": "#22c55e"}
        ]
        
        response = session.put(f"{BASE_URL}/api/projects/{project_id}",
                              headers=auth_headers,
                              json={"task_statuses": new_statuses})
        assert response.status_code == 200
        
        project = response.json()
        assert project["task_statuses"] == new_statuses
    
    def test_project_default_statuses(self, session, auth_headers, org_id):
        """New project without custom statuses should have defaults"""
        response = session.post(f"{BASE_URL}/api/projects/?org_id={org_id}",
                               headers=auth_headers,
                               json={
                                   "name": f"DefaultStatusProject_{UNIQUE_ID}",
                                   "description": "Project with default statuses"
                               })
        assert response.status_code == 200
        
        project = response.json()
        assert "task_statuses" in project
        assert len(project["task_statuses"]) == 4, "Should have 4 default statuses"
        
        # Verify default status IDs
        status_ids = [s["id"] for s in project["task_statuses"]]
        assert "todo" in status_ids
        assert "in_progress" in status_ids
        assert "done" in status_ids


class TestTaskAssignees:
    """Test task assignee_ids field"""
    
    def test_task_has_assignee_ids(self, session, auth_headers, task_id):
        """Task should have assignee_ids field"""
        response = session.get(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        
        task = response.json()
        assert "assignee_ids" in task
        assert isinstance(task["assignee_ids"], list)
    
    def test_update_task_assignees(self, session, auth_headers, task_id, auth_data):
        """Should be able to update task assignees"""
        new_assignees = [auth_data["user"]["user_id"]]
        
        response = session.put(f"{BASE_URL}/api/tasks/{task_id}",
                              headers=auth_headers,
                              json={"assignee_ids": new_assignees})
        assert response.status_code == 200
        
        task = response.json()
        assert task["assignee_ids"] == new_assignees
    
    def test_clear_task_assignees(self, session, auth_headers, task_id):
        """Should be able to clear task assignees"""
        response = session.put(f"{BASE_URL}/api/tasks/{task_id}",
                              headers=auth_headers,
                              json={"assignee_ids": []})
        assert response.status_code == 200
        
        task = response.json()
        assert task["assignee_ids"] == []
    
    def test_create_task_with_assignees(self, session, auth_headers, project_id, auth_data):
        """Should be able to create task with assignees"""
        response = session.post(f"{BASE_URL}/api/tasks/",
                               headers=auth_headers,
                               json={
                                   "title": f"TaskWithAssignee_{UNIQUE_ID}",
                                   "project_id": project_id,
                                   "assignee_ids": [auth_data["user"]["user_id"]]
                               })
        assert response.status_code == 200
        
        task = response.json()
        assert auth_data["user"]["user_id"] in task["assignee_ids"]


class TestTaskActivity:
    """Test GET /api/tasks/{id}/activity endpoint"""
    
    def test_activity_requires_auth(self, session, task_id):
        """Activity endpoint should require authentication"""
        response = session.get(f"{BASE_URL}/api/tasks/{task_id}/activity")
        assert response.status_code == 401
    
    def test_get_task_activity(self, session, auth_headers, task_id):
        """Should return activity log for task"""
        response = session.get(f"{BASE_URL}/api/tasks/{task_id}/activity", headers=auth_headers)
        assert response.status_code == 200
        
        activity = response.json()
        assert isinstance(activity, list)
    
    def test_activity_includes_comments(self, session, auth_headers, task_id):
        """Activity should include comments"""
        # Create a comment first
        comment_text = f"Test comment for activity {UNIQUE_ID}"
        session.post(f"{BASE_URL}/api/comments/",
                    headers=auth_headers,
                    json={"content": comment_text, "task_id": task_id})
        
        # Get activity
        response = session.get(f"{BASE_URL}/api/tasks/{task_id}/activity", headers=auth_headers)
        assert response.status_code == 200
        
        activity = response.json()
        comment_activities = [a for a in activity if a.get("type") == "comment"]
        assert len(comment_activities) >= 1, "Should have comment in activity"
        
        # Verify activity structure
        if comment_activities:
            act = comment_activities[0]
            assert "id" in act
            assert "type" in act
            assert "user_name" in act
            assert "created_at" in act
    
    def test_activity_not_found(self, session, auth_headers):
        """Should return 404 for non-existent task"""
        response = session.get(f"{BASE_URL}/api/tasks/nonexistent_task/activity", headers=auth_headers)
        assert response.status_code == 404


class TestTaskStatusUpdate:
    """Test task status updates (for drag & drop)"""
    
    def test_update_task_status(self, session, auth_headers, task_id):
        """Should be able to update task status"""
        response = session.put(f"{BASE_URL}/api/tasks/{task_id}",
                              headers=auth_headers,
                              json={"status": "in_progress"})
        assert response.status_code == 200
        
        task = response.json()
        assert task["status"] == "in_progress"
    
    def test_update_task_to_done(self, session, auth_headers, task_id):
        """Should be able to mark task as done"""
        response = session.put(f"{BASE_URL}/api/tasks/{task_id}",
                              headers=auth_headers,
                              json={"status": "done"})
        assert response.status_code == 200
        
        task = response.json()
        assert task["status"] == "done"
    
    def test_update_task_back_to_todo(self, session, auth_headers, task_id):
        """Should be able to move task back to todo"""
        response = session.put(f"{BASE_URL}/api/tasks/{task_id}",
                              headers=auth_headers,
                              json={"status": "todo"})
        assert response.status_code == 200
        
        task = response.json()
        assert task["status"] == "todo"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
