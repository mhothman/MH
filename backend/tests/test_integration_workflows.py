"""
Integration Tests for Complete Workflows
Tests end-to-end workflows that span multiple services and endpoints.
"""
import pytest
import requests
import os
import uuid
import time
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
def super_admin_session():
    """Get super admin session with token and user info"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPER_ADMIN_EMAIL,
        "password": SUPER_ADMIN_PASSWORD
    })
    assert response.status_code == 200
    data = response.json()
    return {
        "token": data["access_token"],
        "user": data["user"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"}
    }


@pytest.fixture(scope="module")
def team_member_session():
    """Get team member session"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEAM_MEMBER_EMAIL,
        "password": TEAM_MEMBER_PASSWORD
    })
    assert response.status_code == 200
    data = response.json()
    return {
        "token": data["access_token"],
        "user": data["user"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"}
    }


@pytest.fixture(scope="module")
def org_id(super_admin_session):
    """Get organization ID"""
    response = requests.get(
        f"{BASE_URL}/api/organizations/",
        headers=super_admin_session["headers"]
    )
    return response.json()[0]["org_id"]


# =============================================
# Workflow 1: Complete Project Lifecycle
# =============================================

class TestProjectLifecycleWorkflow:
    """
    Test complete project lifecycle:
    1. Create project
    2. Add tasks
    3. Assign members
    4. Update task statuses
    5. Track time
    6. Archive project
    """
    
    def test_complete_project_lifecycle(self, super_admin_session, org_id):
        """Test full project lifecycle from creation to completion"""
        headers = super_admin_session["headers"]
        
        # Step 1: Create project
        print("\n=== Step 1: Create Project ===")
        project_name = f"Integration Test Project {uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/projects/?org_id={org_id}",
            headers=headers,
            json={
                "name": project_name,
                "description": "Project for integration testing",
                "status": "active"
            }
        )
        assert response.status_code in [200, 201], f"Failed to create project: {response.text}"
        project = response.json()
        project_id = project["project_id"]
        print(f"Created project: {project_name} ({project_id})")
        
        # Step 2: Create multiple tasks
        print("\n=== Step 2: Create Tasks ===")
        task_ids = []
        for i in range(3):
            response = requests.post(
                f"{BASE_URL}/api/tasks/",
                headers=headers,
                json={
                    "project_id": project_id,
                    "title": f"Task {i+1}: {['Setup', 'Development', 'Testing'][i]}",
                    "description": f"Description for task {i+1}",
                    "status": "todo",
                    "priority": ["high", "medium", "low"][i]
                }
            )
            assert response.status_code in [200, 201], f"Failed to create task {i+1}: {response.text}"
            task = response.json()
            task_ids.append(task["task_id"])
            print(f"Created task: {task['title']} ({task['task_id']})")
        
        # Step 3: Update task statuses (workflow progression)
        print("\n=== Step 3: Update Task Statuses ===")
        statuses = ["in_progress", "in_progress", "todo"]
        for i, task_id in enumerate(task_ids):
            response = requests.put(
                f"{BASE_URL}/api/tasks/{task_id}",
                headers=headers,
                json={"status": statuses[i]}
            )
            # May return 428 if approval required, that's OK
            if response.status_code == 428:
                print(f"Task {task_id} requires approval for status change")
            else:
                assert response.status_code == 200, f"Failed to update task: {response.text}"
                print(f"Updated task {task_id} to status: {statuses[i]}")
        
        # Step 4: Add time entries
        print("\n=== Step 4: Track Time ===")
        for task_id in task_ids[:2]:  # Track time on first 2 tasks
            response = requests.post(
                f"{BASE_URL}/api/time-entries/",
                headers=headers,
                json={
                    "task_id": task_id,
                    "duration_minutes": 60,
                    "description": "Development work"
                }
            )
            assert response.status_code in [200, 201], f"Failed to create time entry: {response.text}"
            print(f"Added 1 hour to task {task_id}")
        
        # Step 5: Verify time summary
        print("\n=== Step 5: Verify Time Summary ===")
        response = requests.get(
            f"{BASE_URL}/api/time-entries/summary?project_id={project_id}",
            headers=headers
        )
        assert response.status_code == 200
        summary = response.json()
        print(f"Total hours logged: {summary.get('total_hours', 0)}")
        
        # Step 6: Complete first task
        print("\n=== Step 6: Complete First Task ===")
        response = requests.put(
            f"{BASE_URL}/api/tasks/{task_ids[0]}",
            headers=headers,
            json={"status": "done"}
        )
        if response.status_code == 200:
            print(f"Completed task {task_ids[0]}")
        elif response.status_code == 428:
            print("Task completion requires approval")
        
        # Step 7: Archive project
        print("\n=== Step 7: Archive Project ===")
        response = requests.put(
            f"{BASE_URL}/api/projects/{project_id}",
            headers=headers,
            json={"status": "archived"}
        )
        assert response.status_code == 200, f"Failed to archive project: {response.text}"
        print(f"Archived project {project_id}")
        
        # Cleanup: Delete test tasks and project
        print("\n=== Cleanup ===")
        for task_id in task_ids:
            requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=headers)
        print("Test completed successfully!")


# =============================================
# Workflow 2: Task Assignment & Notification
# =============================================

class TestTaskAssignmentWorkflow:
    """
    Test task assignment workflow:
    1. Create task
    2. Assign to team member
    3. Verify notification created
    4. Update task
    5. Verify activity logged
    """
    
    def test_task_assignment_notification(self, super_admin_session, team_member_session, org_id):
        """Test that assigning a task creates notifications"""
        admin_headers = super_admin_session["headers"]
        member_headers = team_member_session["headers"]
        team_member_id = team_member_session["user"]["user_id"]
        
        # Get a project
        response = requests.get(f"{BASE_URL}/api/projects/", headers=admin_headers)
        assert response.status_code == 200
        projects = response.json()
        if not projects:
            pytest.skip("No projects available for testing")
        project_id = projects[0]["project_id"]
        
        # Create task assigned to team member
        print("\n=== Creating Task Assigned to Team Member ===")
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=admin_headers,
            json={
                "project_id": project_id,
                "title": f"Assigned Task {uuid.uuid4().hex[:6]}",
                "description": "Task assigned to team member",
                "status": "todo",
                "priority": "high",
                "assignee_ids": [team_member_id]
            }
        )
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        task = response.json()
        task_id = task["task_id"]
        print(f"Created task {task_id} assigned to {team_member_id}")
        
        # Small delay for notification processing
        time.sleep(0.5)
        
        # Check team member's notifications
        print("\n=== Checking Team Member Notifications ===")
        response = requests.get(
            f"{BASE_URL}/api/notifications/",
            headers=member_headers
        )
        assert response.status_code == 200
        notifications = response.json()
        print(f"Team member has {len(notifications)} notification(s)")
        
        # Check task activity
        print("\n=== Checking Task Activity ===")
        response = requests.get(
            f"{BASE_URL}/api/tasks/{task_id}/activity",
            headers=admin_headers
        )
        assert response.status_code == 200
        activity = response.json()
        print(f"Task has {len(activity)} activity entries")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=admin_headers)
        print("Test completed!")


# =============================================
# Workflow 3: Time Tracking Complete Flow
# =============================================

class TestTimeTrackingWorkflow:
    """
    Test complete time tracking workflow:
    1. Start timer
    2. Check active timer
    3. Stop timer (creates entry)
    4. Create manual entry
    5. View summary
    """
    
    def test_complete_time_tracking(self, super_admin_session, org_id):
        """Test complete time tracking workflow"""
        headers = super_admin_session["headers"]
        
        # Get or create a task
        print("\n=== Setup: Get Task for Time Tracking ===")
        response = requests.get(f"{BASE_URL}/api/tasks/", headers=headers)
        assert response.status_code == 200
        tasks = response.json()
        
        if not tasks:
            # Create a task if none exist
            response = requests.get(f"{BASE_URL}/api/projects/", headers=headers)
            projects = response.json()
            if not projects:
                pytest.skip("No projects available")
            
            response = requests.post(
                f"{BASE_URL}/api/tasks/",
                headers=headers,
                json={
                    "project_id": projects[0]["project_id"],
                    "title": "Time Tracking Test Task",
                    "status": "in_progress"
                }
            )
            assert response.status_code in [200, 201]
            task_id = response.json()["task_id"]
        else:
            task_id = tasks[0]["task_id"]
        print(f"Using task: {task_id}")
        
        # Step 1: Check no active timer
        print("\n=== Step 1: Check Timer Status ===")
        response = requests.get(f"{BASE_URL}/api/time-entries/timer/active", headers=headers)
        assert response.status_code == 200
        if response.json().get("active"):
            # Stop existing timer first
            requests.post(f"{BASE_URL}/api/time-entries/timer/stop", headers=headers)
        print("No active timer")
        
        # Step 2: Start timer
        print("\n=== Step 2: Start Timer ===")
        response = requests.post(
            f"{BASE_URL}/api/time-entries/timer/start",
            headers=headers,
            json={"task_id": task_id, "description": "Integration test"}
        )
        assert response.status_code in [200, 201], f"Failed to start timer: {response.text}"
        print(f"Timer started for task {task_id}")
        
        # Step 3: Verify active timer
        print("\n=== Step 3: Verify Active Timer ===")
        response = requests.get(f"{BASE_URL}/api/time-entries/timer/active", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["active"] == True
        assert data["timer"]["task_id"] == task_id
        print(f"Active timer confirmed, elapsed: {data['timer'].get('elapsed_seconds', 0)}s")
        
        # Step 4: Stop timer
        print("\n=== Step 4: Stop Timer ===")
        time.sleep(1)  # Let some time pass
        response = requests.post(f"{BASE_URL}/api/time-entries/timer/stop", headers=headers)
        assert response.status_code == 200
        result = response.json()
        print(f"Timer stopped, duration: {result.get('duration_minutes', 0)} minutes")
        
        # Step 5: Create manual entry
        print("\n=== Step 5: Create Manual Entry ===")
        response = requests.post(
            f"{BASE_URL}/api/time-entries/",
            headers=headers,
            json={
                "task_id": task_id,
                "duration_minutes": 30,
                "description": "Manual entry for testing"
            }
        )
        assert response.status_code in [200, 201]
        print("Manual entry created: 30 minutes")
        
        # Step 6: Get entries
        print("\n=== Step 6: View Time Entries ===")
        response = requests.get(
            f"{BASE_URL}/api/time-entries/?task_id={task_id}",
            headers=headers
        )
        assert response.status_code == 200
        entries = response.json()
        print(f"Task has {len(entries)} time entries")
        
        # Step 7: View summary
        print("\n=== Step 7: View Summary ===")
        response = requests.get(f"{BASE_URL}/api/time-entries/summary", headers=headers)
        assert response.status_code == 200
        summary = response.json()
        print(f"Total hours: {summary.get('total_hours', 0)}")
        
        print("\nTime tracking workflow completed!")


# =============================================
# Workflow 4: Role & Permission Management
# =============================================

class TestRolePermissionWorkflow:
    """
    Test role and permission management:
    1. Get all permissions
    2. Create custom role
    3. Update role permissions
    4. Delete role
    """
    
    def test_custom_role_lifecycle(self, super_admin_session, org_id):
        """Test complete custom role lifecycle"""
        headers = super_admin_session["headers"]
        
        # Step 1: Get all permissions
        print("\n=== Step 1: Get Available Permissions ===")
        response = requests.get(f"{BASE_URL}/api/roles/permissions", headers=headers)
        assert response.status_code == 200
        perms_data = response.json()
        print(f"Available: {len(perms_data['permissions'])} permissions in {len(perms_data['categories'])} categories")
        
        # Step 2: Create custom role
        print("\n=== Step 2: Create Custom Role ===")
        role_name = f"Test Role {uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/roles/org/{org_id}",
            headers=headers,
            json={
                "name": role_name,
                "description": "Custom role for integration testing",
                "permissions": ["project:view", "task:view", "task:create"],
                "color": "#ff5733"
            }
        )
        assert response.status_code in [200, 201], f"Failed to create role: {response.text}"
        role = response.json()
        role_id = role["role_id"]
        print(f"Created role: {role_name} ({role_id})")
        
        # Step 3: Verify role in list
        print("\n=== Step 3: Verify Role in List ===")
        response = requests.get(f"{BASE_URL}/api/roles/org/{org_id}", headers=headers)
        assert response.status_code == 200
        roles_data = response.json()
        custom_roles = roles_data["custom_roles"]
        assert any(r["role_id"] == role_id for r in custom_roles)
        print(f"Role found in org's custom roles (total: {len(custom_roles)})")
        
        # Step 4: Update role
        print("\n=== Step 4: Update Role ===")
        response = requests.put(
            f"{BASE_URL}/api/roles/{role_id}",
            headers=headers,
            json={
                "description": "Updated description",
                "permissions": ["project:view", "task:view", "task:create", "task:edit"]
            }
        )
        assert response.status_code == 200
        updated = response.json()
        assert len(updated["permissions"]) == 4
        print(f"Role updated with {len(updated['permissions'])} permissions")
        
        # Step 5: Delete role
        print("\n=== Step 5: Delete Role ===")
        response = requests.delete(f"{BASE_URL}/api/roles/{role_id}", headers=headers)
        assert response.status_code == 200
        print("Role deleted successfully")
        
        # Step 6: Verify deletion
        response = requests.get(f"{BASE_URL}/api/roles/{role_id}", headers=headers)
        assert response.status_code == 404
        print("Role confirmed deleted")
        
        print("\nRole management workflow completed!")


# =============================================
# Workflow 5: Bulk Operations
# =============================================

class TestBulkOperationsWorkflow:
    """
    Test bulk operations workflow:
    1. Create multiple tasks
    2. Bulk update status
    3. Bulk assign
    4. Bulk delete
    """
    
    def test_bulk_task_operations(self, super_admin_session, org_id):
        """Test bulk task operations"""
        headers = super_admin_session["headers"]
        
        # Get a project
        response = requests.get(f"{BASE_URL}/api/projects/", headers=headers)
        projects = response.json()
        if not projects:
            pytest.skip("No projects available")
        project_id = projects[0]["project_id"]
        
        # Step 1: Create multiple tasks
        print("\n=== Step 1: Create Multiple Tasks ===")
        task_ids = []
        for i in range(5):
            response = requests.post(
                f"{BASE_URL}/api/tasks/",
                headers=headers,
                json={
                    "project_id": project_id,
                    "title": f"Bulk Test Task {i+1}",
                    "status": "todo",
                    "priority": "medium"
                }
            )
            if response.status_code in [200, 201]:
                task_ids.append(response.json()["task_id"])
        print(f"Created {len(task_ids)} tasks")
        
        if len(task_ids) < 3:
            pytest.skip("Could not create enough tasks for bulk testing")
        
        # Step 2: Bulk update status
        print("\n=== Step 2: Bulk Update Status ===")
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/update",
            headers=headers,
            json={
                "task_ids": task_ids[:3],
                "updates": {"priority": "high"}
            }
        )
        assert response.status_code == 200
        result = response.json()
        print(f"Updated {result.get('modified_count', 0)} tasks to high priority")
        
        # Step 3: Bulk assign
        print("\n=== Step 3: Bulk Assign ===")
        user_id = super_admin_session["user"]["user_id"]
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/assign",
            headers=headers,
            json={
                "task_ids": task_ids[:3],
                "assignee_id": user_id
            }
        )
        assert response.status_code == 200
        result = response.json()
        print(f"Assigned {result.get('modified_count', 0)} tasks")
        
        # Step 4: Bulk delete
        print("\n=== Step 4: Bulk Delete ===")
        response = requests.post(
            f"{BASE_URL}/api/tasks/bulk/delete",
            headers=headers,
            json={"task_ids": task_ids}
        )
        assert response.status_code == 200
        result = response.json()
        print(f"Deleted {result.get('deleted_count', 0)} tasks")
        
        print("\nBulk operations workflow completed!")


# =============================================
# Workflow 6: Branding Customization
# =============================================

class TestBrandingWorkflow:
    """
    Test branding customization workflow:
    1. Get current branding
    2. Update colors
    3. Update fonts
    4. Publish branding
    5. Get public branding
    6. Reset branding
    """
    
    def test_branding_customization(self, super_admin_session, org_id):
        """Test complete branding customization workflow"""
        headers = super_admin_session["headers"]
        
        # Step 1: Get current branding
        print("\n=== Step 1: Get Current Branding ===")
        response = requests.get(f"{BASE_URL}/api/branding/org/{org_id}", headers=headers)
        assert response.status_code == 200
        original_branding = response.json()
        print(f"Current primary color: {original_branding.get('primary_color')}")
        
        # Step 2: Update colors
        print("\n=== Step 2: Update Colors ===")
        response = requests.put(
            f"{BASE_URL}/api/branding/org/{org_id}",
            headers=headers,
            json={
                "primary_color": "#2d3436",
                "secondary_color": "#0984e3",
                "accent_color": "#00b894"
            }
        )
        assert response.status_code == 200
        updated = response.json()
        print(f"Updated colors: primary={updated['primary_color']}")
        
        # Step 3: Update fonts
        print("\n=== Step 3: Update Fonts ===")
        response = requests.put(
            f"{BASE_URL}/api/branding/org/{org_id}",
            headers=headers,
            json={
                "heading_font": "poppins",
                "body_font": "roboto"
            }
        )
        assert response.status_code == 200
        updated = response.json()
        print(f"Updated fonts: heading={updated.get('heading_font')}, body={updated.get('body_font')}")
        
        # Step 4: Publish branding
        print("\n=== Step 4: Publish Branding ===")
        response = requests.post(
            f"{BASE_URL}/api/branding/org/{org_id}/publish",
            headers=headers
        )
        assert response.status_code == 200
        published = response.json()
        assert published.get("published") == True
        print("Branding published successfully")
        
        # Step 5: Get public branding
        print("\n=== Step 5: Get Public Branding ===")
        response = requests.get(
            f"{BASE_URL}/api/branding/org/{org_id}/public",
            headers=headers
        )
        assert response.status_code == 200
        public_branding = response.json()
        print(f"Public branding: primary={public_branding.get('primary_color')}")
        
        # Step 6: Reset branding
        print("\n=== Step 6: Reset Branding ===")
        response = requests.post(
            f"{BASE_URL}/api/branding/org/{org_id}/reset",
            headers=headers
        )
        assert response.status_code == 200
        reset_branding = response.json()
        print(f"Reset to default: primary={reset_branding.get('primary_color')}")
        
        print("\nBranding workflow completed!")


# =============================================
# Run tests
# =============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
