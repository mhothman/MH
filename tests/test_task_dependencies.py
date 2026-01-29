"""
Backend API Tests for Task Dependencies Feature (Iteration 6):
- blocked_by field - tasks that block this task
- blocks field - tasks that this task blocks
- PUT /api/tasks/{id}/dependencies endpoint
- PUT /api/tasks/{id} with blocked_by and blocks fields
- Blocked indicator logic (task is blocked if any blocked_by task is not done)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://docflows.preview.emergentagent.com')

# Generate unique test user for each test run
UNIQUE_ID = uuid.uuid4().hex[:8]
TEST_USER = {
    "email": f"test_deps_{UNIQUE_ID}@example.com",
    "password": "TestPass123!",
    "name": f"Test Dependencies User {UNIQUE_ID}"
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
                           json={"name": f"Test Org Deps {UNIQUE_ID}"})
    assert response.status_code == 200
    return response.json()["org_id"]


@pytest.fixture(scope="module")
def project_id(session, auth_headers, org_id):
    """Create a test project for dependencies testing"""
    response = session.post(f"{BASE_URL}/api/projects/?org_id={org_id}",
                           headers=auth_headers,
                           json={
                               "name": f"DependenciesTestProject_{UNIQUE_ID}",
                               "description": "Project for testing task dependencies",
                               "status": "active"
                           })
    assert response.status_code == 200, f"Project creation failed: {response.text}"
    return response.json()["project_id"]


@pytest.fixture(scope="module")
def task_ids(session, auth_headers, project_id):
    """Create multiple test tasks for dependency testing"""
    tasks = []
    
    # Create Task A (will be the blocking task)
    response = session.post(f"{BASE_URL}/api/tasks/",
                           headers=auth_headers,
                           json={
                               "title": f"TaskA_Blocker_{UNIQUE_ID}",
                               "description": "This task blocks other tasks",
                               "project_id": project_id,
                               "status": "todo",
                               "priority": "high"
                           })
    assert response.status_code == 200, f"Task A creation failed: {response.text}"
    tasks.append(response.json()["task_id"])
    
    # Create Task B (will be blocked by Task A)
    response = session.post(f"{BASE_URL}/api/tasks/",
                           headers=auth_headers,
                           json={
                               "title": f"TaskB_Blocked_{UNIQUE_ID}",
                               "description": "This task is blocked by Task A",
                               "project_id": project_id,
                               "status": "todo",
                               "priority": "medium"
                           })
    assert response.status_code == 200, f"Task B creation failed: {response.text}"
    tasks.append(response.json()["task_id"])
    
    # Create Task C (will be blocked by Task B)
    response = session.post(f"{BASE_URL}/api/tasks/",
                           headers=auth_headers,
                           json={
                               "title": f"TaskC_ChainBlocked_{UNIQUE_ID}",
                               "description": "This task is blocked by Task B",
                               "project_id": project_id,
                               "status": "todo",
                               "priority": "low"
                           })
    assert response.status_code == 200, f"Task C creation failed: {response.text}"
    tasks.append(response.json()["task_id"])
    
    return tasks  # [task_a_id, task_b_id, task_c_id]


class TestTaskDependenciesFields:
    """Test that tasks have blocked_by and blocks fields"""
    
    def test_task_has_blocked_by_field(self, session, auth_headers, task_ids):
        """Task should have blocked_by field"""
        task_id = task_ids[0]
        response = session.get(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        
        task = response.json()
        assert "blocked_by" in task, "Task should have blocked_by field"
        assert isinstance(task["blocked_by"], list), "blocked_by should be a list"
    
    def test_task_has_blocks_field(self, session, auth_headers, task_ids):
        """Task should have blocks field"""
        task_id = task_ids[0]
        response = session.get(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        
        task = response.json()
        assert "blocks" in task, "Task should have blocks field"
        assert isinstance(task["blocks"], list), "blocks should be a list"
    
    def test_create_task_with_dependencies(self, session, auth_headers, project_id, task_ids):
        """Should be able to create task with blocked_by and blocks"""
        task_a_id = task_ids[0]
        
        response = session.post(f"{BASE_URL}/api/tasks/",
                               headers=auth_headers,
                               json={
                                   "title": f"TaskWithDeps_{UNIQUE_ID}",
                                   "project_id": project_id,
                                   "blocked_by": [task_a_id],
                                   "blocks": []
                               })
        assert response.status_code == 200, f"Task creation failed: {response.text}"
        
        task = response.json()
        assert task_a_id in task["blocked_by"], "Task should be blocked by Task A"


class TestUpdateDependenciesViaTaskUpdate:
    """Test updating dependencies via PUT /api/tasks/{id}"""
    
    def test_update_blocked_by_via_task_update(self, session, auth_headers, task_ids):
        """Should be able to update blocked_by via task update"""
        task_a_id, task_b_id, _ = task_ids
        
        response = session.put(f"{BASE_URL}/api/tasks/{task_b_id}",
                              headers=auth_headers,
                              json={"blocked_by": [task_a_id]})
        assert response.status_code == 200
        
        task = response.json()
        assert task_a_id in task["blocked_by"], "Task B should be blocked by Task A"
    
    def test_update_blocks_via_task_update(self, session, auth_headers, task_ids):
        """Should be able to update blocks via task update"""
        task_a_id, task_b_id, _ = task_ids
        
        response = session.put(f"{BASE_URL}/api/tasks/{task_a_id}",
                              headers=auth_headers,
                              json={"blocks": [task_b_id]})
        assert response.status_code == 200
        
        task = response.json()
        assert task_b_id in task["blocks"], "Task A should block Task B"
    
    def test_clear_dependencies(self, session, auth_headers, task_ids):
        """Should be able to clear dependencies"""
        _, task_b_id, _ = task_ids
        
        response = session.put(f"{BASE_URL}/api/tasks/{task_b_id}",
                              headers=auth_headers,
                              json={"blocked_by": [], "blocks": []})
        assert response.status_code == 200
        
        task = response.json()
        assert task["blocked_by"] == [], "blocked_by should be empty"
        assert task["blocks"] == [], "blocks should be empty"


class TestDependenciesEndpoint:
    """Test PUT /api/tasks/{id}/dependencies endpoint"""
    
    def test_dependencies_endpoint_requires_auth(self, session, task_ids):
        """Dependencies endpoint should require authentication"""
        task_id = task_ids[0]
        response = session.put(f"{BASE_URL}/api/tasks/{task_id}/dependencies")
        assert response.status_code == 401
    
    def test_update_dependencies_via_endpoint(self, session, auth_headers, task_ids):
        """Should be able to update dependencies via dedicated endpoint"""
        task_a_id, task_b_id, task_c_id = task_ids
        
        # Set Task B blocked by Task A
        response = session.put(
            f"{BASE_URL}/api/tasks/{task_b_id}/dependencies",
            headers=auth_headers,
            params={"blocked_by": [task_a_id], "blocks": [task_c_id]}
        )
        assert response.status_code == 200, f"Dependencies update failed: {response.text}"
        
        # Verify the update
        response = session.get(f"{BASE_URL}/api/tasks/{task_b_id}", headers=auth_headers)
        assert response.status_code == 200
        task = response.json()
        assert task_a_id in task["blocked_by"], "Task B should be blocked by Task A"
        assert task_c_id in task["blocks"], "Task B should block Task C"
    
    def test_dependencies_endpoint_validates_task_exists(self, session, auth_headers, task_ids):
        """Dependencies endpoint should validate that referenced tasks exist"""
        task_id = task_ids[0]
        
        response = session.put(
            f"{BASE_URL}/api/tasks/{task_id}/dependencies",
            headers=auth_headers,
            params={"blocked_by": ["nonexistent_task_id"], "blocks": []}
        )
        assert response.status_code == 400, "Should return 400 for non-existent task reference"
    
    def test_dependencies_endpoint_not_found(self, session, auth_headers):
        """Dependencies endpoint should return 404 for non-existent task"""
        response = session.put(
            f"{BASE_URL}/api/tasks/nonexistent_task/dependencies",
            headers=auth_headers,
            params={"blocked_by": [], "blocks": []}
        )
        assert response.status_code == 404


class TestBlockedIndicatorLogic:
    """Test the blocked indicator logic - task is blocked if any blocked_by task is not done"""
    
    def test_task_blocked_when_blocker_not_done(self, session, auth_headers, task_ids):
        """Task should be considered blocked when blocking task is not done"""
        task_a_id, task_b_id, _ = task_ids
        
        # Ensure Task A is not done
        session.put(f"{BASE_URL}/api/tasks/{task_a_id}",
                   headers=auth_headers,
                   json={"status": "todo"})
        
        # Set Task B blocked by Task A
        session.put(f"{BASE_URL}/api/tasks/{task_b_id}",
                   headers=auth_headers,
                   json={"blocked_by": [task_a_id]})
        
        # Get Task B and verify blocked_by contains Task A
        response = session.get(f"{BASE_URL}/api/tasks/{task_b_id}", headers=auth_headers)
        assert response.status_code == 200
        task_b = response.json()
        assert task_a_id in task_b["blocked_by"]
        
        # Get Task A status
        response = session.get(f"{BASE_URL}/api/tasks/{task_a_id}", headers=auth_headers)
        task_a = response.json()
        assert task_a["status"] != "done", "Task A should not be done"
    
    def test_task_unblocked_when_blocker_done(self, session, auth_headers, task_ids):
        """Task should be unblocked when blocking task is marked as done"""
        task_a_id, task_b_id, _ = task_ids
        
        # Set Task B blocked by Task A
        session.put(f"{BASE_URL}/api/tasks/{task_b_id}",
                   headers=auth_headers,
                   json={"blocked_by": [task_a_id]})
        
        # Mark Task A as done
        response = session.put(f"{BASE_URL}/api/tasks/{task_a_id}",
                              headers=auth_headers,
                              json={"status": "done"})
        assert response.status_code == 200
        
        # Verify Task A is done
        response = session.get(f"{BASE_URL}/api/tasks/{task_a_id}", headers=auth_headers)
        task_a = response.json()
        assert task_a["status"] == "done", "Task A should be done"
        
        # Task B still has blocked_by but the blocker is done
        response = session.get(f"{BASE_URL}/api/tasks/{task_b_id}", headers=auth_headers)
        task_b = response.json()
        assert task_a_id in task_b["blocked_by"], "blocked_by should still contain Task A"


class TestMultipleDependencies:
    """Test multiple dependencies scenarios"""
    
    def test_task_blocked_by_multiple_tasks(self, session, auth_headers, project_id, task_ids):
        """Task can be blocked by multiple tasks"""
        task_a_id, task_b_id, task_c_id = task_ids
        
        # Create a new task blocked by both A and B
        response = session.post(f"{BASE_URL}/api/tasks/",
                               headers=auth_headers,
                               json={
                                   "title": f"MultiBlockedTask_{UNIQUE_ID}",
                                   "project_id": project_id,
                                   "blocked_by": [task_a_id, task_b_id]
                               })
        assert response.status_code == 200
        
        task = response.json()
        assert len(task["blocked_by"]) == 2
        assert task_a_id in task["blocked_by"]
        assert task_b_id in task["blocked_by"]
    
    def test_task_blocks_multiple_tasks(self, session, auth_headers, task_ids):
        """Task can block multiple tasks"""
        task_a_id, task_b_id, task_c_id = task_ids
        
        # Set Task A to block both B and C
        response = session.put(f"{BASE_URL}/api/tasks/{task_a_id}",
                              headers=auth_headers,
                              json={"blocks": [task_b_id, task_c_id]})
        assert response.status_code == 200
        
        task = response.json()
        assert len(task["blocks"]) == 2
        assert task_b_id in task["blocks"]
        assert task_c_id in task["blocks"]


class TestGetTasksWithDependencies:
    """Test that GET /api/tasks returns dependency fields"""
    
    def test_get_tasks_includes_dependencies(self, session, auth_headers, project_id, task_ids):
        """GET /api/tasks should include blocked_by and blocks fields"""
        response = session.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=auth_headers)
        assert response.status_code == 200
        
        tasks = response.json()
        assert len(tasks) >= 3, "Should have at least 3 tasks"
        
        for task in tasks:
            assert "blocked_by" in task, f"Task {task['task_id']} should have blocked_by field"
            assert "blocks" in task, f"Task {task['task_id']} should have blocks field"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
