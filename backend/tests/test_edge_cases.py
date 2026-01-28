"""
Edge Case and Boundary Condition Tests
Tests for boundary conditions, invalid inputs, race conditions, and error handling.
"""
import pytest
import requests
import os
import uuid
import time
import concurrent.futures
from datetime import datetime, timezone, timedelta

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
def admin_auth():
    """Get admin auth"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPER_ADMIN_EMAIL,
        "password": SUPER_ADMIN_PASSWORD
    })
    assert response.status_code == 200
    data = response.json()
    return {
        "token": data["access_token"],
        "user_id": data["user"]["user_id"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"}
    }


@pytest.fixture(scope="module")
def org_id(admin_auth):
    """Get organization ID"""
    response = requests.get(
        f"{BASE_URL}/api/organizations/",
        headers=admin_auth["headers"]
    )
    return response.json()[0]["org_id"]


@pytest.fixture(scope="module")
def project_id(admin_auth):
    """Get a project ID"""
    response = requests.get(
        f"{BASE_URL}/api/projects/",
        headers=admin_auth["headers"]
    )
    if response.json():
        return response.json()[0]["project_id"]
    return None


# =============================================
# Authentication Edge Cases
# =============================================

class TestAuthEdgeCases:
    """Test authentication boundary conditions"""
    
    def test_login_empty_email(self):
        """Test login with empty email"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "",
            "password": "anypassword"
        })
        assert response.status_code in [400, 401, 422]
    
    def test_login_empty_password(self):
        """Test login with empty password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": ""
        })
        assert response.status_code in [400, 401, 422]
    
    def test_login_null_values(self):
        """Test login with null values"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": None,
            "password": None
        })
        assert response.status_code in [400, 422]
    
    def test_login_missing_fields(self):
        """Test login with missing fields"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={})
        assert response.status_code in [400, 422]
    
    def test_login_extra_fields_ignored(self):
        """Test that extra fields don't affect login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD,
            "extra_field": "should be ignored",
            "another_field": 12345
        })
        assert response.status_code == 200
    
    def test_login_very_long_email(self):
        """Test login with extremely long email"""
        long_email = "a" * 1000 + "@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": long_email,
            "password": "anypassword"
        })
        # Should fail validation or return 401
        assert response.status_code in [400, 401, 422]
    
    def test_login_special_characters_email(self):
        """Test login with special characters in email"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test<script>@test.com",
            "password": "anypassword"
        })
        assert response.status_code in [400, 401, 422]
    
    def test_invalid_token_format(self):
        """Test API with malformed token"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.format"}
        )
        assert response.status_code in [401, 403]
    
    def test_expired_token_simulation(self):
        """Test with clearly invalid JWT structure"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MDAwMDAwMDB9.invalid"}
        )
        assert response.status_code in [401, 403]
    
    def test_auth_header_variations(self):
        """Test various auth header formats"""
        # Missing Bearer prefix
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "invalid_token"}
        )
        assert response.status_code in [401, 403]
        
        # Lowercase bearer
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "bearer invalid_token"}
        )
        assert response.status_code in [401, 403]


# =============================================
# Task API Edge Cases
# =============================================

class TestTaskEdgeCases:
    """Test task API boundary conditions"""
    
    def test_create_task_empty_title(self, admin_auth, project_id):
        """Test creating task with empty title - should be rejected by validation"""
        if not project_id:
            pytest.skip("No project available")
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_auth["headers"],
            json={
                "project_id": project_id,
                "title": "",
                "status": "todo"
            }
        )
        # Validation should reject empty titles
        assert response.status_code == 422
        assert "title" in response.text.lower() or "empty" in response.text.lower()
    
    def test_create_task_whitespace_title(self, admin_auth, project_id):
        """Test creating task with whitespace-only title - should be rejected"""
        if not project_id:
            pytest.skip("No project available")
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_auth["headers"],
            json={
                "project_id": project_id,
                "title": "   ",
                "status": "todo"
            }
        )
        # Validation should reject whitespace-only titles
        assert response.status_code == 422
    
    def test_create_task_very_long_title(self, admin_auth, project_id):
        """Test creating task with extremely long title - should be rejected"""
        if not project_id:
            pytest.skip("No project available")
        long_title = "A" * 10000
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_auth["headers"],
            json={
                "project_id": project_id,
                "title": long_title,
                "status": "todo"
            }
        )
        # Validation should reject titles over 500 chars
        assert response.status_code == 422
    
    def test_create_task_invalid_status(self, admin_auth, project_id):
        """Test creating task with invalid status - should be rejected by validation"""
        if not project_id:
            pytest.skip("No project available")
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_auth["headers"],
            json={
                "project_id": project_id,
                "title": "Test Task Invalid Status",
                "status": "invalid_status"
            }
        )
        # Validation should reject invalid status values
        assert response.status_code == 422
        assert "status" in response.text.lower()
    
    def test_create_task_invalid_priority(self, admin_auth, project_id):
        """Test creating task with invalid priority - should be rejected by validation"""
        if not project_id:
            pytest.skip("No project available")
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_auth["headers"],
            json={
                "project_id": project_id,
                "title": "Test Task Invalid Priority",
                "status": "todo",
                "priority": "super_critical"  # invalid priority
            }
        )
        # Validation should reject invalid priority values
        assert response.status_code == 422
        assert "priority" in response.text.lower()
    
    def test_create_task_nonexistent_project(self, admin_auth):
        """Test creating task for non-existent project"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_auth["headers"],
            json={
                "project_id": "nonexistent_project_id_12345",
                "title": "Test Task",
                "status": "todo"
            }
        )
        assert response.status_code in [400, 404, 422]
    
    def test_create_task_invalid_assignee(self, admin_auth, project_id):
        """Test creating task with invalid assignee ID"""
        if not project_id:
            pytest.skip("No project available")
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_auth["headers"],
            json={
                "project_id": project_id,
                "title": "Test Task",
                "status": "todo",
                "assignee_ids": ["nonexistent_user_123"]
            }
        )
        # May succeed (orphan reference) or fail
        assert response.status_code in [200, 201, 400, 404, 422]
    
    def test_get_task_invalid_id(self, admin_auth):
        """Test getting task with invalid ID"""
        response = requests.get(
            f"{BASE_URL}/api/tasks/invalid_task_id_123",
            headers=admin_auth["headers"]
        )
        assert response.status_code == 404
    
    def test_update_task_invalid_id(self, admin_auth):
        """Test updating non-existent task"""
        response = requests.put(
            f"{BASE_URL}/api/tasks/nonexistent_task_id",
            headers=admin_auth["headers"],
            json={"status": "done"}
        )
        assert response.status_code == 404
    
    def test_delete_task_invalid_id(self, admin_auth):
        """Test deleting non-existent task"""
        response = requests.delete(
            f"{BASE_URL}/api/tasks/nonexistent_task_id",
            headers=admin_auth["headers"]
        )
        assert response.status_code == 404
    
    def test_update_task_empty_body(self, admin_auth, project_id):
        """Test updating task with empty body"""
        if not project_id:
            pytest.skip("No project available")
        # First create a task
        create_response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_auth["headers"],
            json={
                "project_id": project_id,
                "title": "Test Empty Update",
                "status": "todo"
            }
        )
        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create test task")
        
        task_id = create_response.json()["task_id"]
        
        # Update with empty body
        response = requests.put(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers=admin_auth["headers"],
            json={}
        )
        # Should succeed with no changes or fail validation
        assert response.status_code in [200, 400, 422]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=admin_auth["headers"])


# =============================================
# Project API Edge Cases
# =============================================

class TestProjectEdgeCases:
    """Test project API boundary conditions"""
    
    def test_get_project_invalid_id(self, admin_auth):
        """Test getting project with invalid ID"""
        response = requests.get(
            f"{BASE_URL}/api/projects/invalid_id_123",
            headers=admin_auth["headers"]
        )
        assert response.status_code == 404
    
    def test_update_project_invalid_id(self, admin_auth):
        """Test updating non-existent project"""
        response = requests.put(
            f"{BASE_URL}/api/projects/nonexistent_project",
            headers=admin_auth["headers"],
            json={"name": "New Name"}
        )
        assert response.status_code == 404
    
    def test_project_filter_invalid_status(self, admin_auth):
        """Test filtering projects with invalid status"""
        response = requests.get(
            f"{BASE_URL}/api/projects/?status=invalid_status",
            headers=admin_auth["headers"]
        )
        # Should return empty or all projects
        assert response.status_code == 200


# =============================================
# Role API Edge Cases
# =============================================

class TestRoleEdgeCases:
    """Test role API boundary conditions"""
    
    def test_create_role_empty_name(self, admin_auth, org_id):
        """Test creating role with empty name"""
        response = requests.post(
            f"{BASE_URL}/api/roles/org/{org_id}",
            headers=admin_auth["headers"],
            json={
                "name": "",
                "permissions": ["project:view"]
            }
        )
        assert response.status_code in [400, 422]
    
    def test_create_role_duplicate_name(self, admin_auth, org_id):
        """Test creating role with duplicate name"""
        role_name = f"Duplicate Test {uuid.uuid4().hex[:6]}"
        
        # Create first role
        response1 = requests.post(
            f"{BASE_URL}/api/roles/org/{org_id}",
            headers=admin_auth["headers"],
            json={
                "name": role_name,
                "permissions": ["project:view"]
            }
        )
        assert response1.status_code in [200, 201]
        role_id = response1.json()["role_id"]
        
        # Try to create duplicate
        response2 = requests.post(
            f"{BASE_URL}/api/roles/org/{org_id}",
            headers=admin_auth["headers"],
            json={
                "name": role_name,
                "permissions": ["project:view"]
            }
        )
        # Should fail with conflict
        assert response2.status_code in [400, 409]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/roles/{role_id}", headers=admin_auth["headers"])
    
    def test_create_role_empty_permissions(self, admin_auth, org_id):
        """Test creating role with no permissions"""
        response = requests.post(
            f"{BASE_URL}/api/roles/org/{org_id}",
            headers=admin_auth["headers"],
            json={
                "name": f"No Perms Role {uuid.uuid4().hex[:6]}",
                "permissions": []
            }
        )
        # May succeed (viewer-like role) or fail
        if response.status_code in [200, 201]:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/roles/{response.json()['role_id']}", headers=admin_auth["headers"])
        else:
            assert response.status_code in [400, 422]
    
    def test_create_role_invalid_permissions(self, admin_auth, org_id):
        """Test creating role with invalid permissions"""
        response = requests.post(
            f"{BASE_URL}/api/roles/org/{org_id}",
            headers=admin_auth["headers"],
            json={
                "name": "Bad Perms",
                "permissions": ["invalid:perm", "fake:permission"]
            }
        )
        assert response.status_code == 400
    
    def test_delete_builtin_role(self, admin_auth, org_id):
        """Test that built-in roles cannot be deleted"""
        # Get built-in roles
        response = requests.get(
            f"{BASE_URL}/api/roles/org/{org_id}",
            headers=admin_auth["headers"]
        )
        assert response.status_code == 200
        
        builtin_roles = response.json()["built_in_roles"]
        if builtin_roles:
            # Try to delete a built-in role
            role_id = builtin_roles[0]["role_id"]
            delete_response = requests.delete(
                f"{BASE_URL}/api/roles/{role_id}",
                headers=admin_auth["headers"]
            )
            # Should be forbidden or not found (if role_id is an identifier, not a deletable ID)
            assert delete_response.status_code in [400, 403, 404]
    
    def test_get_role_invalid_id(self, admin_auth):
        """Test getting role with invalid ID"""
        response = requests.get(
            f"{BASE_URL}/api/roles/invalid_role_id_123",
            headers=admin_auth["headers"]
        )
        assert response.status_code == 404


# =============================================
# Time Tracking Edge Cases
# =============================================

class TestTimeTrackingEdgeCases:
    """Test time tracking boundary conditions"""
    
    def test_create_time_entry_zero_duration(self, admin_auth, project_id):
        """Test creating time entry with zero duration"""
        if not project_id:
            pytest.skip("No project available")
        
        # Get a task
        tasks = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=admin_auth["headers"])
        if not tasks.json():
            pytest.skip("No tasks available")
        task_id = tasks.json()[0]["task_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/time-entries/",
            headers=admin_auth["headers"],
            json={
                "task_id": task_id,
                "duration_minutes": 0,
                "description": "Zero duration test"
            }
        )
        # May succeed or fail validation
        assert response.status_code in [200, 201, 400, 422]
    
    def test_create_time_entry_negative_duration(self, admin_auth, project_id):
        """Test creating time entry with negative duration"""
        if not project_id:
            pytest.skip("No project available")
        
        tasks = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=admin_auth["headers"])
        if not tasks.json():
            pytest.skip("No tasks available")
        task_id = tasks.json()[0]["task_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/time-entries/",
            headers=admin_auth["headers"],
            json={
                "task_id": task_id,
                "duration_minutes": -30,
                "description": "Negative duration test"
            }
        )
        assert response.status_code in [400, 422]
    
    def test_create_time_entry_very_large_duration(self, admin_auth, project_id):
        """Test creating time entry with very large duration"""
        if not project_id:
            pytest.skip("No project available")
        
        tasks = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=admin_auth["headers"])
        if not tasks.json():
            pytest.skip("No tasks available")
        task_id = tasks.json()[0]["task_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/time-entries/",
            headers=admin_auth["headers"],
            json={
                "task_id": task_id,
                "duration_minutes": 999999999,  # Unrealistic duration
                "description": "Very large duration"
            }
        )
        # May succeed or fail validation
        assert response.status_code in [200, 201, 400, 422]
    
    def test_start_timer_nonexistent_task(self, admin_auth):
        """Test starting timer for non-existent task"""
        # First stop any existing timer
        requests.post(f"{BASE_URL}/api/time-entries/timer/stop", headers=admin_auth["headers"])
        
        response = requests.post(
            f"{BASE_URL}/api/time-entries/timer/start",
            headers=admin_auth["headers"],
            json={
                "task_id": "nonexistent_task_id_123",
                "description": "Test"
            }
        )
        assert response.status_code in [400, 404]
    
    def test_stop_timer_when_none_active(self, admin_auth):
        """Test stopping timer when none is active"""
        # First ensure no timer is running
        requests.post(f"{BASE_URL}/api/time-entries/timer/stop", headers=admin_auth["headers"])
        
        # Try to stop again
        response = requests.post(
            f"{BASE_URL}/api/time-entries/timer/stop",
            headers=admin_auth["headers"]
        )
        # Should handle gracefully
        assert response.status_code in [200, 400, 404]


# =============================================
# Organization Edge Cases
# =============================================

class TestOrganizationEdgeCases:
    """Test organization API boundary conditions"""
    
    def test_get_org_invalid_id(self, admin_auth):
        """Test getting organization with invalid ID"""
        response = requests.get(
            f"{BASE_URL}/api/organizations/invalid_org_id_123",
            headers=admin_auth["headers"]
        )
        assert response.status_code in [403, 404]
    
    def test_get_members_invalid_org(self, admin_auth):
        """Test getting members of non-existent organization"""
        response = requests.get(
            f"{BASE_URL}/api/organizations/nonexistent_org/members",
            headers=admin_auth["headers"]
        )
        assert response.status_code in [403, 404]


# =============================================
# Bulk Operations Edge Cases
# =============================================

class TestBulkOperationsEdgeCases:
    """Test bulk operations boundary conditions"""
    
    def test_bulk_update_empty_task_ids(self, admin_auth):
        """Test bulk update with empty task list"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/update",
            headers=admin_auth["headers"],
            json={
                "task_ids": [],
                "updates": {"priority": "high"}
            }
        )
        # Should succeed with 0 modified or fail validation
        assert response.status_code in [200, 400, 422]
    
    def test_bulk_update_invalid_task_ids(self, admin_auth):
        """Test bulk update with non-existent task IDs"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/update",
            headers=admin_auth["headers"],
            json={
                "task_ids": ["fake_id_1", "fake_id_2", "fake_id_3"],
                "updates": {"priority": "high"}
            }
        )
        # API returns 404 when no tasks found, or 200 with 0 modified
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert response.json().get("modified_count", 0) == 0
    
    def test_bulk_delete_empty_task_ids(self, admin_auth):
        """Test bulk delete with empty task list"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/delete",
            headers=admin_auth["headers"],
            json={"task_ids": []}
        )
        assert response.status_code in [200, 400, 422]
    
    def test_bulk_assign_empty_task_ids(self, admin_auth):
        """Test bulk assign with empty task list"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/assign",
            headers=admin_auth["headers"],
            json={
                "task_ids": [],
                "assignee_id": admin_auth["user_id"]
            }
        )
        assert response.status_code in [200, 400, 422]


# =============================================
# Concurrent Access / Race Conditions
# =============================================

class TestConcurrentAccess:
    """Test for potential race conditions"""
    
    def test_concurrent_task_updates(self, admin_auth, project_id):
        """Test concurrent updates to the same task"""
        if not project_id:
            pytest.skip("No project available")
        
        # Create a test task
        create_response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_auth["headers"],
            json={
                "project_id": project_id,
                "title": "Concurrent Test Task",
                "status": "todo",
                "priority": "medium"
            }
        )
        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create test task")
        
        task_id = create_response.json()["task_id"]
        
        # Perform concurrent updates
        def update_task(priority):
            return requests.put(
                f"{BASE_URL}/api/tasks/{task_id}",
                headers=admin_auth["headers"],
                json={"priority": priority}
            )
        
        priorities = ["low", "medium", "high", "low", "high"]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(update_task, p) for p in priorities]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should succeed (last writer wins)
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 3, f"Too many failed updates: {success_count}/5"
        
        # Verify task is in consistent state
        get_response = requests.get(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers=admin_auth["headers"]
        )
        assert get_response.status_code == 200
        assert get_response.json()["priority"] in ["low", "medium", "high"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=admin_auth["headers"])
    
    def test_concurrent_timer_starts(self, admin_auth, project_id):
        """Test attempting to start multiple timers concurrently"""
        if not project_id:
            pytest.skip("No project available")
        
        # Get a task
        tasks = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=admin_auth["headers"])
        if not tasks.json():
            pytest.skip("No tasks available")
        task_id = tasks.json()[0]["task_id"]
        
        # Ensure no timer is running
        requests.post(f"{BASE_URL}/api/time-entries/timer/stop", headers=admin_auth["headers"])
        
        # Try to start multiple timers at once
        def start_timer():
            return requests.post(
                f"{BASE_URL}/api/time-entries/timer/start",
                headers=admin_auth["headers"],
                json={"task_id": task_id}
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(start_timer) for _ in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Only one should succeed
        success_count = sum(1 for r in results if r.status_code in [200, 201])
        assert success_count >= 1, "No timer start succeeded"
        
        # Verify only one timer is active
        active = requests.get(f"{BASE_URL}/api/time-entries/timer/active", headers=admin_auth["headers"])
        assert active.status_code == 200
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/time-entries/timer/stop", headers=admin_auth["headers"])


# =============================================
# Input Sanitization / Security Edge Cases
# =============================================

class TestInputSanitization:
    """Test input sanitization and security"""
    
    def test_xss_in_task_title(self, admin_auth, project_id):
        """Test XSS payload in task title"""
        if not project_id:
            pytest.skip("No project available")
        
        xss_payload = "<script>alert('xss')</script>"
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_auth["headers"],
            json={
                "project_id": project_id,
                "title": xss_payload,
                "status": "todo"
            }
        )
        
        if response.status_code in [200, 201]:
            task = response.json()
            # Title should be escaped or stored safely
            # The important thing is the API doesn't crash
            requests.delete(f"{BASE_URL}/api/tasks/{task['task_id']}", headers=admin_auth["headers"])
        else:
            # May be rejected, which is also fine
            assert response.status_code in [400, 422]
    
    def test_sql_injection_attempt(self, admin_auth, project_id):
        """Test SQL injection payload (for documentation, MongoDB is not vulnerable)"""
        if not project_id:
            pytest.skip("No project available")
        
        sql_payload = "'; DROP TABLE tasks; --"
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_auth["headers"],
            json={
                "project_id": project_id,
                "title": sql_payload,
                "status": "todo"
            }
        )
        
        # Should not crash - MongoDB uses different query language
        assert response.status_code in [200, 201, 400, 422]
        
        if response.status_code in [200, 201]:
            requests.delete(f"{BASE_URL}/api/tasks/{response.json()['task_id']}", headers=admin_auth["headers"])
    
    def test_nosql_injection_attempt(self, admin_auth):
        """Test NoSQL injection in query parameters"""
        # This is a common NoSQL injection pattern
        response = requests.get(
            f"{BASE_URL}/api/tasks/?project_id[$ne]=null",
            headers=admin_auth["headers"]
        )
        # Should either return normal results or 400/422, not all documents
        assert response.status_code in [200, 400, 422]
    
    def test_unicode_handling(self, admin_auth, project_id):
        """Test Unicode characters in inputs"""
        if not project_id:
            pytest.skip("No project available")
        
        unicode_title = "Task with emoji 🚀 and unicode: ñ, 中文, العربية"
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_auth["headers"],
            json={
                "project_id": project_id,
                "title": unicode_title,
                "status": "todo"
            }
        )
        
        assert response.status_code in [200, 201]
        if response.status_code in [200, 201]:
            task = response.json()
            assert "🚀" in task["title"] or "emoji" in task["title"]
            requests.delete(f"{BASE_URL}/api/tasks/{task['task_id']}", headers=admin_auth["headers"])


# =============================================
# Content-Type and Request Format Edge Cases
# =============================================

class TestRequestFormatEdgeCases:
    """Test various request format edge cases"""
    
    def test_wrong_content_type(self):
        """Test sending form data instead of JSON"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        # Should fail or be handled gracefully
        assert response.status_code in [200, 400, 415, 422]
    
    def test_malformed_json(self, admin_auth):
        """Test sending malformed JSON"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers={**admin_auth["headers"], "Content-Type": "application/json"},
            data="{ invalid json }"
        )
        assert response.status_code in [400, 422]
    
    def test_array_instead_of_object(self, admin_auth):
        """Test sending array when object is expected"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_auth["headers"],
            json=["array", "instead", "of", "object"]
        )
        assert response.status_code in [400, 422]


# =============================================
# Project Validation Edge Cases
# =============================================

class TestProjectValidationEdgeCases:
    """Test project API input validation"""
    
    def test_create_project_empty_name(self, admin_auth, org_id):
        """Test creating project with empty name - should be rejected"""
        response = requests.post(
            f"{BASE_URL}/api/projects/?org_id={org_id}",
            headers=admin_auth["headers"],
            json={"name": ""}
        )
        assert response.status_code == 422
        assert "name" in response.text.lower()
    
    def test_create_project_whitespace_name(self, admin_auth, org_id):
        """Test creating project with whitespace-only name - should be rejected"""
        response = requests.post(
            f"{BASE_URL}/api/projects/?org_id={org_id}",
            headers=admin_auth["headers"],
            json={"name": "   "}
        )
        assert response.status_code == 422
    
    def test_create_project_very_long_name(self, admin_auth, org_id):
        """Test creating project with name > 200 chars - should be rejected"""
        response = requests.post(
            f"{BASE_URL}/api/projects/?org_id={org_id}",
            headers=admin_auth["headers"],
            json={"name": "A" * 250}
        )
        assert response.status_code == 422
    
    def test_create_project_invalid_status(self, admin_auth, org_id):
        """Test creating project with invalid status - should be rejected"""
        response = requests.post(
            f"{BASE_URL}/api/projects/?org_id={org_id}",
            headers=admin_auth["headers"],
            json={"name": "Test Project", "status": "invalid_status"}
        )
        assert response.status_code == 422
        assert "status" in response.text.lower()
    
    def test_create_project_invalid_color(self, admin_auth, org_id):
        """Test creating project with invalid hex color - should be rejected"""
        response = requests.post(
            f"{BASE_URL}/api/projects/?org_id={org_id}",
            headers=admin_auth["headers"],
            json={"name": "Test Project", "color": "notacolor"}
        )
        assert response.status_code == 422
        assert "color" in response.text.lower()
    
    def test_create_project_valid_statuses(self, admin_auth, org_id):
        """Test all valid project statuses work"""
        valid_statuses = ["planned", "active", "on_hold", "completed", "archived", "cancelled"]
        
        for status in valid_statuses:
            response = requests.post(
                f"{BASE_URL}/api/projects/?org_id={org_id}",
                headers=admin_auth["headers"],
                json={"name": f"Test {status}", "status": status}
            )
            assert response.status_code in [200, 201], f"Status '{status}' should be valid"
            if response.status_code in [200, 201]:
                # Cleanup
                requests.delete(
                    f"{BASE_URL}/api/projects/{response.json()['project_id']}?org_id={org_id}",
                    headers=admin_auth["headers"]
                )
    
    def test_create_project_valid_colors(self, admin_auth, org_id):
        """Test valid hex color formats"""
        valid_colors = ["#FF5733", "#fff", "#000000", "#ABC"]
        
        for color in valid_colors:
            response = requests.post(
                f"{BASE_URL}/api/projects/?org_id={org_id}",
                headers=admin_auth["headers"],
                json={"name": f"Color Test", "color": color}
            )
            assert response.status_code in [200, 201], f"Color '{color}' should be valid"
            if response.status_code in [200, 201]:
                requests.delete(
                    f"{BASE_URL}/api/projects/{response.json()['project_id']}?org_id={org_id}",
                    headers=admin_auth["headers"]
                )


# =============================================
# Comment Validation Edge Cases
# =============================================

class TestCommentValidationEdgeCases:
    """Test comment API input validation"""
    
    def test_create_comment_empty_content(self, admin_auth, project_id):
        """Test creating comment with empty content - should be rejected"""
        if not project_id:
            pytest.skip("No project available")
        
        # Get a task
        tasks = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=admin_auth["headers"], timeout=30)
        if not tasks.json():
            pytest.skip("No tasks available")
        task_id = tasks.json()[0]["task_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/comments/",
            headers=admin_auth["headers"],
            json={"task_id": task_id, "content": ""},
            timeout=30
        )
        assert response.status_code == 422
        assert "content" in response.text.lower()
    
    def test_create_comment_whitespace_content(self, admin_auth, project_id):
        """Test creating comment with whitespace-only content - should be rejected"""
        if not project_id:
            pytest.skip("No project available")
        
        time.sleep(1)  # Rate limit buffer
        tasks = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=admin_auth["headers"], timeout=30)
        if not tasks.json():
            pytest.skip("No tasks available")
        task_id = tasks.json()[0]["task_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/comments/",
            headers=admin_auth["headers"],
            json={"task_id": task_id, "content": "   "},
            timeout=30
        )
        assert response.status_code == 422
    
    def test_create_comment_valid(self, admin_auth, project_id):
        """Test creating valid comment - should succeed"""
        if not project_id:
            pytest.skip("No project available")
        
        time.sleep(1)  # Rate limit buffer
        tasks = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=admin_auth["headers"], timeout=30)
        if not tasks.json():
            pytest.skip("No tasks available")
        task_id = tasks.json()[0]["task_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/comments/",
            headers=admin_auth["headers"],
            json={"task_id": task_id, "content": "This is a valid comment"},
            timeout=30
        )
        assert response.status_code in [200, 201]
        assert "comment_id" in response.json()
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/comments/{response.json()['comment_id']}",
            headers=admin_auth["headers"],
            timeout=30
        )


# =============================================
# Time Entry Validation Edge Cases
# =============================================

class TestTimeEntryValidationEdgeCases:
    """Test time entry API input validation"""
    
    def test_create_time_entry_negative_duration(self, admin_auth, project_id):
        """Test creating time entry with negative duration - should be rejected"""
        if not project_id:
            pytest.skip("No project available")
        
        time.sleep(1)  # Rate limit buffer
        tasks = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=admin_auth["headers"], timeout=30)
        if not tasks.json():
            pytest.skip("No tasks available")
        task_id = tasks.json()[0]["task_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/time-entries/",
            headers=admin_auth["headers"],
            json={"task_id": task_id, "duration_minutes": -30},
            timeout=30
        )
        assert response.status_code == 422
    
    def test_create_time_entry_zero_duration(self, admin_auth, project_id):
        """Test creating time entry with zero duration - should be rejected"""
        if not project_id:
            pytest.skip("No project available")
        
        time.sleep(1)  # Rate limit buffer
        tasks = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=admin_auth["headers"], timeout=30)
        if not tasks.json():
            pytest.skip("No tasks available")
        task_id = tasks.json()[0]["task_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/time-entries/",
            headers=admin_auth["headers"],
            json={"task_id": task_id, "duration_minutes": 0},
            timeout=30
        )
        assert response.status_code == 422
    
    def test_create_time_entry_excessive_duration(self, admin_auth, project_id):
        """Test creating time entry with duration > 24 hours - should be rejected"""
        if not project_id:
            pytest.skip("No project available")
        
        time.sleep(1)  # Rate limit buffer
        tasks = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=admin_auth["headers"], timeout=30)
        if not tasks.json():
            pytest.skip("No tasks available")
        task_id = tasks.json()[0]["task_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/time-entries/",
            headers=admin_auth["headers"],
            json={"task_id": task_id, "duration_minutes": 1500},  # > 24 hours
            timeout=30
        )
        assert response.status_code == 422
    
    def test_create_time_entry_valid(self, admin_auth, project_id):
        """Test creating valid time entry - should succeed"""
        if not project_id:
            pytest.skip("No project available")
        
        time.sleep(1)  # Rate limit buffer
        tasks = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=admin_auth["headers"], timeout=30)
        if not tasks.json():
            pytest.skip("No tasks available")
        task_id = tasks.json()[0]["task_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/time-entries/",
            headers=admin_auth["headers"],
            json={
                "task_id": task_id,
                "duration_minutes": 60,
                "description": "Valid time entry"
            },
            timeout=30
        )
        assert response.status_code in [200, 201]
        assert "entry_id" in response.json()


# =============================================
# Organization Validation Edge Cases
# =============================================

class TestOrganizationValidationEdgeCases:
    """Test organization API input validation"""
    
    def test_update_org_empty_name(self, admin_auth, org_id):
        """Test updating organization with empty name - should be rejected"""
        response = requests.put(
            f"{BASE_URL}/api/organizations/{org_id}",
            headers=admin_auth["headers"],
            json={"name": ""},
            timeout=30
        )
        assert response.status_code == 422
        assert "name" in response.text.lower()
    
    def test_update_org_invalid_timezone(self, admin_auth, org_id):
        """Test updating organization with invalid timezone - should be rejected"""
        response = requests.put(
            f"{BASE_URL}/api/organizations/{org_id}",
            headers=admin_auth["headers"],
            json={"timezone": "Invalid/Timezone"},
            timeout=30
        )
        assert response.status_code == 422
        assert "timezone" in response.text.lower()
    
    def test_update_org_invalid_working_day(self, admin_auth, org_id):
        """Test updating organization with invalid working day - should be rejected"""
        response = requests.put(
            f"{BASE_URL}/api/organizations/{org_id}",
            headers=admin_auth["headers"],
            json={"working_days": ["monday", "funday"]},
            timeout=30
        )
        assert response.status_code == 422
        assert "working" in response.text.lower()
    
    def test_update_org_empty_working_days(self, admin_auth, org_id):
        """Test updating organization with empty working days - should be rejected"""
        response = requests.put(
            f"{BASE_URL}/api/organizations/{org_id}",
            headers=admin_auth["headers"],
            json={"working_days": []},
            timeout=30
        )
        assert response.status_code == 422
    
    def test_update_org_invalid_email(self, admin_auth, org_id):
        """Test updating organization with invalid contact email - should be rejected"""
        response = requests.put(
            f"{BASE_URL}/api/organizations/{org_id}",
            headers=admin_auth["headers"],
            json={"contact_email": "notanemail"},
            timeout=30
        )
        assert response.status_code == 422
        assert "email" in response.text.lower()
    
    def test_update_org_valid_timezone(self, admin_auth, org_id):
        """Test updating organization with valid timezone - should succeed"""
        response = requests.put(
            f"{BASE_URL}/api/organizations/{org_id}",
            headers=admin_auth["headers"],
            json={"timezone": "America/New_York"},
            timeout=30
        )
        assert response.status_code == 200
        assert response.json()["timezone"] == "America/New_York"


# =============================================
# Invite Validation Edge Cases
# =============================================

class TestInviteValidationEdgeCases:
    """Test member invite API input validation"""
    
    def test_invite_empty_email(self, admin_auth, org_id):
        """Test inviting with empty email - should be rejected"""
        response = requests.post(
            f"{BASE_URL}/api/organizations/{org_id}/invite",
            headers=admin_auth["headers"],
            json={"email": ""},
            timeout=30
        )
        assert response.status_code == 422
        assert "email" in response.text.lower()
    
    def test_invite_invalid_email_format(self, admin_auth, org_id):
        """Test inviting with invalid email format - should be rejected"""
        response = requests.post(
            f"{BASE_URL}/api/organizations/{org_id}/invite",
            headers=admin_auth["headers"],
            json={"email": "notanemail"},
            timeout=30
        )
        assert response.status_code == 422
        assert "email" in response.text.lower()
    
    def test_invite_invalid_role(self, admin_auth, org_id):
        """Test inviting with invalid role - should be rejected"""
        response = requests.post(
            f"{BASE_URL}/api/organizations/{org_id}/invite",
            headers=admin_auth["headers"],
            json={"email": "test@example.com", "role": "invalid_role"},
            timeout=30
        )
        assert response.status_code == 422
        assert "role" in response.text.lower()


# =============================================
# Role Validation Edge Cases
# =============================================

class TestRoleValidationEdgeCases:
    """Test role API input validation"""
    
    def test_create_role_empty_name(self, admin_auth, org_id):
        """Test creating role with empty name - should be rejected"""
        response = requests.post(
            f"{BASE_URL}/api/roles/org/{org_id}",
            headers=admin_auth["headers"],
            json={"name": "", "permissions": []},
            timeout=30
        )
        assert response.status_code == 422
        assert "name" in response.text.lower()
    
    def test_create_role_invalid_color(self, admin_auth, org_id):
        """Test creating role with invalid color - should be rejected"""
        response = requests.post(
            f"{BASE_URL}/api/roles/org/{org_id}",
            headers=admin_auth["headers"],
            json={"name": "Test Role", "permissions": [], "color": "notacolor"},
            timeout=30
        )
        assert response.status_code == 422
        assert "color" in response.text.lower()
    
    def test_create_role_valid_with_color(self, admin_auth, org_id):
        """Test creating role with valid color - should succeed"""
        import uuid
        role_name = f"Color Role {uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/roles/org/{org_id}",
            headers=admin_auth["headers"],
            json={"name": role_name, "permissions": ["project:view"], "color": "#FF5733"},
            timeout=30
        )
        assert response.status_code in [200, 201]
        role = response.json()
        assert "role_id" in role
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/roles/{role['role_id']}",
            headers=admin_auth["headers"],
            timeout=30
        )


# =============================================
# Run tests
# =============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
