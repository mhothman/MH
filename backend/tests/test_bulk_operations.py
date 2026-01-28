"""
Test Bulk Task Operations and Task Title Editing
Tests for:
- POST /api/tasks/bulk/update - Bulk update tasks
- POST /api/tasks/bulk/assign - Bulk assign tasks
- POST /api/tasks/bulk/delete - Bulk delete tasks
- PUT /api/tasks/{task_id} - Task title editing
- Existing task CRUD operations (regression)
- Customer CRUD (regression)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Test credentials
TEST_EMAIL = "test@proflow.com"
TEST_PASSWORD = "test123456"


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data


class TestTaskCRUD:
    """Task CRUD operations - regression tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def project_id(self, auth_headers):
        """Get first available project"""
        response = requests.get(f"{BASE_URL}/api/projects/", headers=auth_headers)
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) > 0, "No projects found"
        return projects[0]["project_id"]
    
    def test_get_tasks(self, auth_headers, project_id):
        """Test getting tasks for a project"""
        response = requests.get(
            f"{BASE_URL}/api/tasks/?project_id={project_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        tasks = response.json()
        assert isinstance(tasks, list)
        print(f"Found {len(tasks)} tasks in project")
    
    def test_create_task(self, auth_headers, project_id):
        """Test creating a new task"""
        task_data = {
            "project_id": project_id,
            "title": f"TEST_BulkOps_Task_{uuid.uuid4().hex[:8]}",
            "description": "Test task for bulk operations testing",
            "status": "todo",
            "priority": "medium",
            "assignee_ids": []
        }
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            json=task_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Create task failed: {response.text}"
        data = response.json()
        assert "task_id" in data
        assert data["title"] == task_data["title"]
        return data["task_id"]
    
    def test_update_task_title(self, auth_headers, project_id):
        """Test updating task title - key feature for inline editing"""
        # Create a task first
        task_data = {
            "project_id": project_id,
            "title": f"TEST_TitleEdit_Original_{uuid.uuid4().hex[:8]}",
            "status": "todo",
            "priority": "medium",
            "assignee_ids": []
        }
        create_response = requests.post(
            f"{BASE_URL}/api/tasks/",
            json=task_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        task_id = create_response.json()["task_id"]
        
        # Update the title
        new_title = f"TEST_TitleEdit_Updated_{uuid.uuid4().hex[:8]}"
        update_response = requests.put(
            f"{BASE_URL}/api/tasks/{task_id}",
            json={"title": new_title},
            headers=auth_headers
        )
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        updated_task = update_response.json()
        assert updated_task["title"] == new_title, "Title was not updated"
        
        # Verify with GET
        get_response = requests.get(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        assert get_response.json()["title"] == new_title
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
        print(f"Task title editing works: '{task_data['title']}' -> '{new_title}'")
    
    def test_delete_task(self, auth_headers, project_id):
        """Test deleting a task"""
        # Create a task to delete
        task_data = {
            "project_id": project_id,
            "title": f"TEST_ToDelete_{uuid.uuid4().hex[:8]}",
            "status": "todo",
            "priority": "low",
            "assignee_ids": []
        }
        create_response = requests.post(
            f"{BASE_URL}/api/tasks/",
            json=task_data,
            headers=auth_headers
        )
        task_id = create_response.json()["task_id"]
        
        # Delete the task
        delete_response = requests.delete(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404


class TestBulkOperations:
    """Bulk task operations tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def project_id(self, auth_headers):
        """Get first available project"""
        response = requests.get(f"{BASE_URL}/api/projects/", headers=auth_headers)
        projects = response.json()
        return projects[0]["project_id"]
    
    @pytest.fixture(scope="class")
    def test_tasks(self, auth_headers, project_id):
        """Create test tasks for bulk operations"""
        task_ids = []
        for i in range(3):
            task_data = {
                "project_id": project_id,
                "title": f"TEST_BulkTask_{i}_{uuid.uuid4().hex[:8]}",
                "status": "todo",
                "priority": "low",
                "assignee_ids": []
            }
            response = requests.post(
                f"{BASE_URL}/api/tasks/",
                json=task_data,
                headers=auth_headers
            )
            if response.status_code == 200:
                task_ids.append(response.json()["task_id"])
        
        yield task_ids
        
        # Cleanup - delete any remaining test tasks
        for task_id in task_ids:
            try:
                requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
            except:
                pass
    
    def test_bulk_update_status(self, auth_headers, project_id):
        """Test bulk update - change status of multiple tasks"""
        # Create tasks for this test
        task_ids = []
        for i in range(2):
            task_data = {
                "project_id": project_id,
                "title": f"TEST_BulkStatus_{i}_{uuid.uuid4().hex[:8]}",
                "status": "todo",
                "priority": "low",
                "assignee_ids": []
            }
            response = requests.post(
                f"{BASE_URL}/api/tasks/",
                json=task_data,
                headers=auth_headers
            )
            if response.status_code == 200:
                task_ids.append(response.json()["task_id"])
        
        assert len(task_ids) >= 2, "Need at least 2 tasks for bulk update test"
        
        # Bulk update status
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/update",
            json={
                "task_ids": task_ids,
                "updates": {"status": "in_progress"}
            },
            headers=auth_headers
        )
        assert response.status_code == 200, f"Bulk update failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert data["modified_count"] >= 1
        print(f"Bulk update status: modified {data['modified_count']} tasks")
        
        # Verify updates
        for task_id in task_ids:
            get_response = requests.get(
                f"{BASE_URL}/api/tasks/{task_id}",
                headers=auth_headers
            )
            if get_response.status_code == 200:
                assert get_response.json()["status"] == "in_progress"
        
        # Cleanup
        for task_id in task_ids:
            requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
    
    def test_bulk_update_priority(self, auth_headers, project_id):
        """Test bulk update - change priority of multiple tasks"""
        # Create tasks
        task_ids = []
        for i in range(2):
            task_data = {
                "project_id": project_id,
                "title": f"TEST_BulkPriority_{i}_{uuid.uuid4().hex[:8]}",
                "status": "todo",
                "priority": "low",
                "assignee_ids": []
            }
            response = requests.post(
                f"{BASE_URL}/api/tasks/",
                json=task_data,
                headers=auth_headers
            )
            if response.status_code == 200:
                task_ids.append(response.json()["task_id"])
        
        # Bulk update priority
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/update",
            json={
                "task_ids": task_ids,
                "updates": {"priority": "high"}
            },
            headers=auth_headers
        )
        assert response.status_code == 200, f"Bulk priority update failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        print(f"Bulk update priority: modified {data['modified_count']} tasks")
        
        # Cleanup
        for task_id in task_ids:
            requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
    
    def test_bulk_update_empty_tasks(self, auth_headers):
        """Test bulk update with empty task list - should fail"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/update",
            json={
                "task_ids": [],
                "updates": {"status": "done"}
            },
            headers=auth_headers
        )
        assert response.status_code == 400
    
    def test_bulk_update_invalid_field(self, auth_headers, project_id):
        """Test bulk update with invalid field - should ignore invalid fields"""
        # Create a task
        task_data = {
            "project_id": project_id,
            "title": f"TEST_BulkInvalid_{uuid.uuid4().hex[:8]}",
            "status": "todo",
            "priority": "low",
            "assignee_ids": []
        }
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            json=task_data,
            headers=auth_headers
        )
        task_id = response.json()["task_id"]
        
        # Try to update with invalid field
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/update",
            json={
                "task_ids": [task_id],
                "updates": {"invalid_field": "value"}
            },
            headers=auth_headers
        )
        # Should return 400 because no valid updates provided
        assert response.status_code == 400
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
    
    def test_bulk_assign(self, auth_headers, project_id):
        """Test bulk assign - assign user to multiple tasks"""
        # Get a user to assign
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert me_response.status_code == 200
        user_id = me_response.json()["user_id"]
        
        # Create tasks
        task_ids = []
        for i in range(2):
            task_data = {
                "project_id": project_id,
                "title": f"TEST_BulkAssign_{i}_{uuid.uuid4().hex[:8]}",
                "status": "todo",
                "priority": "low",
                "assignee_ids": []
            }
            response = requests.post(
                f"{BASE_URL}/api/tasks/",
                json=task_data,
                headers=auth_headers
            )
            if response.status_code == 200:
                task_ids.append(response.json()["task_id"])
        
        # Bulk assign
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/assign",
            json={
                "task_ids": task_ids,
                "assignee_id": user_id
            },
            headers=auth_headers
        )
        assert response.status_code == 200, f"Bulk assign failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        print(f"Bulk assign: assigned {data['modified_count']} tasks to user")
        
        # Verify assignments
        for task_id in task_ids:
            get_response = requests.get(
                f"{BASE_URL}/api/tasks/{task_id}",
                headers=auth_headers
            )
            if get_response.status_code == 200:
                assert user_id in get_response.json().get("assignee_ids", [])
        
        # Cleanup
        for task_id in task_ids:
            requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
    
    def test_bulk_assign_empty_tasks(self, auth_headers):
        """Test bulk assign with empty task list - should fail"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/assign",
            json={
                "task_ids": [],
                "assignee_id": "some_user_id"
            },
            headers=auth_headers
        )
        assert response.status_code == 400
    
    def test_bulk_delete(self, auth_headers, project_id):
        """Test bulk delete - delete multiple tasks at once"""
        # Create tasks to delete
        task_ids = []
        for i in range(3):
            task_data = {
                "project_id": project_id,
                "title": f"TEST_BulkDelete_{i}_{uuid.uuid4().hex[:8]}",
                "status": "todo",
                "priority": "low",
                "assignee_ids": []
            }
            response = requests.post(
                f"{BASE_URL}/api/tasks/",
                json=task_data,
                headers=auth_headers
            )
            if response.status_code == 200:
                task_ids.append(response.json()["task_id"])
        
        assert len(task_ids) >= 2, "Need at least 2 tasks for bulk delete test"
        
        # Bulk delete
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/delete",
            json={"task_ids": task_ids},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Bulk delete failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert data["deleted_count"] >= 1
        print(f"Bulk delete: deleted {data['deleted_count']} tasks")
        
        # Verify deletions
        for task_id in task_ids:
            get_response = requests.get(
                f"{BASE_URL}/api/tasks/{task_id}",
                headers=auth_headers
            )
            assert get_response.status_code == 404, f"Task {task_id} should be deleted"
    
    def test_bulk_delete_empty_tasks(self, auth_headers):
        """Test bulk delete with empty task list - should fail"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/delete",
            json={"task_ids": []},
            headers=auth_headers
        )
        assert response.status_code == 400
    
    def test_bulk_operations_require_auth(self):
        """Test that bulk operations require authentication"""
        # Bulk update without auth
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/update",
            json={"task_ids": ["task_123"], "updates": {"status": "done"}}
        )
        assert response.status_code == 401
        
        # Bulk assign without auth
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/assign",
            json={"task_ids": ["task_123"], "assignee_id": "user_123"}
        )
        assert response.status_code == 401
        
        # Bulk delete without auth
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/delete",
            json={"task_ids": ["task_123"]}
        )
        assert response.status_code == 401


class TestCustomerCRUD:
    """Customer CRUD regression tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def org_id(self, auth_headers):
        """Get org_id from user"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        user = response.json()
        # Get org from memberships
        memberships_response = requests.get(
            f"{BASE_URL}/api/organizations/memberships",
            headers=auth_headers
        )
        if memberships_response.status_code == 200:
            memberships = memberships_response.json()
            if memberships:
                return memberships[0]["org_id"]
        return None
    
    def test_get_customers(self, auth_headers, org_id):
        """Test getting customers list"""
        if not org_id:
            pytest.skip("No org_id available")
        
        response = requests.get(
            f"{BASE_URL}/api/customers/?org_id={org_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        customers = response.json()
        assert isinstance(customers, list)
        print(f"Found {len(customers)} customers")
    
    def test_create_and_delete_customer(self, auth_headers, org_id):
        """Test creating and deleting a customer"""
        if not org_id:
            pytest.skip("No org_id available")
        
        # Create customer
        customer_data = {
            "org_id": org_id,
            "name": f"TEST_BulkOps_Customer_{uuid.uuid4().hex[:8]}",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "company": "Test Company"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/customers/",
            json=customer_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200, f"Create customer failed: {create_response.text}"
        customer = create_response.json()
        assert "customer_id" in customer
        customer_id = customer["customer_id"]
        
        # Delete customer
        delete_response = requests.delete(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        print("Customer CRUD working correctly")


class TestHealthCheck:
    """Health check tests"""
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
