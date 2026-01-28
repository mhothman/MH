"""
Test Suite for Task Approval Workflows Feature
Tests all workflow CRUD, approval request/approve/reject flows
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Test credentials
TEST_EMAIL = "test@proflow.com"
TEST_PASSWORD = "test123456"
TEST_ORG_ID = "org_3a0711d3f937"
TEST_PROJECT_ID = "proj_c31c1308e3dc"


class TestWorkflowApprovals:
    """Test suite for workflow approval feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.token = None
        self.user_id = None
        
    def authenticate(self):
        """Authenticate and get token"""
        if self.token:
            return self.token
            
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")  # API returns access_token
        self.user_id = data.get("user", {}).get("user_id")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        return self.token
    
    # ==================== Authentication Tests ====================
    
    def test_01_login_success(self):
        """Test login with valid credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data  # API returns access_token
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print(f"✓ Login successful, user_id: {data['user']['user_id']}")
    
    # ==================== Workflow CRUD Tests ====================
    
    def test_02_get_project_workflows(self):
        """Test GET /api/workflows/project/{project_id}"""
        self.authenticate()
        response = self.session.get(f"{BASE_URL}/api/workflows/project/{TEST_PROJECT_ID}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} workflows for project")
        if data:
            print(f"  First workflow: {data[0].get('name')} (ID: {data[0].get('workflow_id')})")
    
    def test_03_create_workflow(self):
        """Test POST /api/workflows/ - Create new workflow"""
        self.authenticate()
        workflow_data = {
            "project_id": TEST_PROJECT_ID,
            "name": "TEST_Approval_Workflow",
            "description": "Test workflow for automated testing",
            "active": True
        }
        response = self.session.post(f"{BASE_URL}/api/workflows/", json=workflow_data)
        assert response.status_code in [200, 201], f"Create workflow failed: {response.text}"
        data = response.json()
        assert "workflow_id" in data
        assert data["name"] == workflow_data["name"]
        assert data["project_id"] == TEST_PROJECT_ID
        assert data["active"] == True
        print(f"✓ Created workflow: {data['workflow_id']}")
        # Store for later tests
        self.__class__.test_workflow_id = data["workflow_id"]
    
    def test_04_get_workflow_by_id(self):
        """Test GET /api/workflows/{workflow_id}"""
        self.authenticate()
        workflow_id = getattr(self.__class__, 'test_workflow_id', None)
        if not workflow_id:
            pytest.skip("No workflow created in previous test")
        
        response = self.session.get(f"{BASE_URL}/api/workflows/{workflow_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == workflow_id
        print(f"✓ Retrieved workflow: {data['name']}")
    
    # ==================== Workflow Rule Tests ====================
    
    def test_05_create_workflow_rule(self):
        """Test POST /api/workflows/{workflow_id}/rules - Create approval rule"""
        self.authenticate()
        workflow_id = getattr(self.__class__, 'test_workflow_id', None)
        if not workflow_id:
            pytest.skip("No workflow created in previous test")
        
        rule_data = {
            "workflow_id": workflow_id,
            "from_status": "todo",
            "to_status": "done",
            "approval_required": True,
            "approval_type": "single",
            "approver_role": "org_admin",
            "notify_on_request": True,
            "notify_on_resolution": True
        }
        response = self.session.post(f"{BASE_URL}/api/workflows/{workflow_id}/rules", json=rule_data)
        assert response.status_code in [200, 201], f"Create rule failed: {response.text}"
        data = response.json()
        assert "rule_id" in data
        assert data["from_status"] == "todo"
        assert data["to_status"] == "done"
        assert data["approval_required"] == True
        print(f"✓ Created rule: {data['rule_id']} (todo -> done)")
        self.__class__.test_rule_id = data["rule_id"]
    
    def test_06_get_workflow_rules(self):
        """Test GET /api/workflows/{workflow_id}/rules"""
        self.authenticate()
        workflow_id = getattr(self.__class__, 'test_workflow_id', None)
        if not workflow_id:
            pytest.skip("No workflow created in previous test")
        
        response = self.session.get(f"{BASE_URL}/api/workflows/{workflow_id}/rules")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        print(f"✓ Got {len(data)} rules for workflow")
    
    # ==================== Task Creation for Approval Testing ====================
    
    def test_07_create_test_task(self):
        """Create a task in 'todo' status for approval testing"""
        self.authenticate()
        task_data = {
            "title": "TEST_Task_For_Approval",
            "description": "Task created for approval workflow testing",
            "status": "todo",
            "priority": "medium",
            "project_id": TEST_PROJECT_ID
        }
        response = self.session.post(f"{BASE_URL}/api/tasks/", json=task_data)
        assert response.status_code in [200, 201], f"Create task failed: {response.text}"
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "todo"
        print(f"✓ Created test task: {data['task_id']}")
        self.__class__.test_task_id = data["task_id"]
    
    # ==================== Approval Check Tests ====================
    
    def test_08_check_approval_required(self):
        """Test GET /api/workflows/tasks/{task_id}/check-approval"""
        self.authenticate()
        task_id = getattr(self.__class__, 'test_task_id', None)
        if not task_id:
            pytest.skip("No task created in previous test")
        
        # Check if approval is required for todo -> done
        response = self.session.get(
            f"{BASE_URL}/api/workflows/tasks/{task_id}/check-approval",
            params={"target_status": "done"}
        )
        assert response.status_code == 200, f"Check approval failed: {response.text}"
        data = response.json()
        assert "requires_approval" in data
        print(f"✓ Approval required for todo->done: {data['requires_approval']}")
        if data.get("rule"):
            print(f"  Rule: {data['rule'].get('rule_id')}")
    
    def test_09_check_approval_not_required(self):
        """Test check-approval for transition that doesn't need approval"""
        self.authenticate()
        task_id = getattr(self.__class__, 'test_task_id', None)
        if not task_id:
            pytest.skip("No task created in previous test")
        
        # Check if approval is required for todo -> in_progress (should not be)
        response = self.session.get(
            f"{BASE_URL}/api/workflows/tasks/{task_id}/check-approval",
            params={"target_status": "in_progress"}
        )
        assert response.status_code == 200
        data = response.json()
        # This transition should NOT require approval (no rule for it)
        print(f"✓ Approval required for todo->in_progress: {data.get('requires_approval', False)}")
    
    # ==================== Request Approval Tests ====================
    
    def test_10_request_approval(self):
        """Test POST /api/workflows/tasks/{task_id}/request-approval"""
        self.authenticate()
        task_id = getattr(self.__class__, 'test_task_id', None)
        if not task_id:
            pytest.skip("No task created in previous test")
        
        request_data = {
            "target_status": "done",
            "comment": "Requesting approval for testing"
        }
        response = self.session.post(
            f"{BASE_URL}/api/workflows/tasks/{task_id}/request-approval",
            json=request_data
        )
        assert response.status_code in [200, 201], f"Request approval failed: {response.text}"
        data = response.json()
        assert "approval_id" in data or "approval" in data
        approval = data.get("approval", data)
        print(f"✓ Approval requested: {approval.get('approval_id')}")
        self.__class__.test_approval_id = approval.get("approval_id")
    
    def test_11_verify_task_locked(self):
        """Verify task is locked after approval request"""
        self.authenticate()
        task_id = getattr(self.__class__, 'test_task_id', None)
        if not task_id:
            pytest.skip("No task created in previous test")
        
        response = self.session.get(f"{BASE_URL}/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("approval_locked") == True, "Task should be locked"
        print(f"✓ Task is locked: {data.get('approval_locked')}")
    
    def test_12_task_update_blocked_when_locked(self):
        """Test that task updates are blocked when locked"""
        self.authenticate()
        task_id = getattr(self.__class__, 'test_task_id', None)
        if not task_id:
            pytest.skip("No task created in previous test")
        
        # Try to update the locked task
        response = self.session.put(
            f"{BASE_URL}/api/tasks/{task_id}",
            json={"title": "Updated Title"}
        )
        # Should return 423 Locked
        assert response.status_code == 423, f"Expected 423 Locked, got {response.status_code}"
        print(f"✓ Task update correctly blocked with 423 status")
    
    # ==================== Approval Summary Tests ====================
    
    def test_13_get_task_approval_summary(self):
        """Test GET /api/workflows/tasks/{task_id}/approval-summary"""
        self.authenticate()
        task_id = getattr(self.__class__, 'test_task_id', None)
        if not task_id:
            pytest.skip("No task created in previous test")
        
        response = self.session.get(f"{BASE_URL}/api/workflows/tasks/{task_id}/approval-summary")
        assert response.status_code == 200, f"Get summary failed: {response.text}"
        data = response.json()
        assert "has_pending_approval" in data
        assert "is_locked" in data
        assert data["has_pending_approval"] == True
        assert data["is_locked"] == True
        print(f"✓ Approval summary: pending={data['has_pending_approval']}, locked={data['is_locked']}")
        if data.get("pending_approval"):
            print(f"  Target status: {data['pending_approval'].get('target_status')}")
    
    # ==================== Pending Approvals Tests ====================
    
    def test_14_get_pending_approvals(self):
        """Test GET /api/workflows/pending"""
        self.authenticate()
        response = self.session.get(f"{BASE_URL}/api/workflows/pending")
        assert response.status_code == 200, f"Get pending failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} pending approvals")
        if data:
            print(f"  First pending: task={data[0].get('task_title')}, status={data[0].get('status')}")
    
    # ==================== Approve/Reject Tests ====================
    
    def test_15_approve_request(self):
        """Test POST /api/workflows/approvals/{approval_id}/approve"""
        self.authenticate()
        approval_id = getattr(self.__class__, 'test_approval_id', None)
        if not approval_id:
            pytest.skip("No approval created in previous test")
        
        response = self.session.post(
            f"{BASE_URL}/api/workflows/approvals/{approval_id}/approve",
            json={"action": "approve", "comment": "Approved via automated test"}
        )
        assert response.status_code == 200, f"Approve failed: {response.text}"
        data = response.json()
        print(f"✓ Approval approved: {data.get('message', 'success')}")
    
    def test_16_verify_task_status_changed(self):
        """Verify task status changed after approval"""
        self.authenticate()
        task_id = getattr(self.__class__, 'test_task_id', None)
        if not task_id:
            pytest.skip("No task created in previous test")
        
        response = self.session.get(f"{BASE_URL}/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done", f"Expected status 'done', got '{data['status']}'"
        assert data.get("approval_locked") == False, "Task should be unlocked"
        print(f"✓ Task status changed to 'done' and unlocked")
    
    # ==================== Rejection Flow Tests ====================
    
    def test_17_create_task_for_rejection(self):
        """Create another task for rejection testing"""
        self.authenticate()
        task_data = {
            "title": "TEST_Task_For_Rejection",
            "description": "Task for rejection flow testing",
            "status": "todo",
            "priority": "low",
            "project_id": TEST_PROJECT_ID
        }
        response = self.session.post(f"{BASE_URL}/api/tasks/", json=task_data)
        assert response.status_code in [200, 201]
        data = response.json()
        print(f"✓ Created task for rejection: {data['task_id']}")
        self.__class__.reject_task_id = data["task_id"]
    
    def test_18_request_approval_for_rejection(self):
        """Request approval that will be rejected"""
        self.authenticate()
        task_id = getattr(self.__class__, 'reject_task_id', None)
        if not task_id:
            pytest.skip("No task created")
        
        response = self.session.post(
            f"{BASE_URL}/api/workflows/tasks/{task_id}/request-approval",
            json={"target_status": "done", "comment": "Will be rejected"}
        )
        assert response.status_code in [200, 201]
        data = response.json()
        approval = data.get("approval", data)
        print(f"✓ Approval requested: {approval.get('approval_id')}")
        self.__class__.reject_approval_id = approval.get("approval_id")
    
    def test_19_reject_request(self):
        """Test POST /api/workflows/approvals/{approval_id}/reject"""
        self.authenticate()
        approval_id = getattr(self.__class__, 'reject_approval_id', None)
        if not approval_id:
            pytest.skip("No approval created")
        
        response = self.session.post(
            f"{BASE_URL}/api/workflows/approvals/{approval_id}/reject",
            json={"action": "reject", "comment": "Rejected via automated test"}
        )
        assert response.status_code == 200, f"Reject failed: {response.text}"
        data = response.json()
        print(f"✓ Approval rejected: {data.get('message', 'success')}")
    
    def test_20_verify_task_unchanged_after_rejection(self):
        """Verify task status unchanged after rejection"""
        self.authenticate()
        task_id = getattr(self.__class__, 'reject_task_id', None)
        if not task_id:
            pytest.skip("No task created")
        
        response = self.session.get(f"{BASE_URL}/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "todo", f"Expected status 'todo', got '{data['status']}'"
        assert data.get("approval_locked") == False, "Task should be unlocked after rejection"
        print(f"✓ Task status unchanged ('todo') and unlocked after rejection")
    
    # ==================== Status Change Blocking Tests ====================
    
    def test_21_direct_status_change_blocked(self):
        """Test that direct status change is blocked when approval required"""
        self.authenticate()
        # Create a new task
        task_data = {
            "title": "TEST_Direct_Status_Change",
            "status": "todo",
            "priority": "medium",
            "project_id": TEST_PROJECT_ID
        }
        response = self.session.post(f"{BASE_URL}/api/tasks/", json=task_data)
        assert response.status_code in [200, 201]
        task_id = response.json()["task_id"]
        
        # Try to directly change status to 'done' (should be blocked)
        response = self.session.put(
            f"{BASE_URL}/api/tasks/{task_id}",
            json={"status": "done"}
        )
        # Should return 428 Precondition Required
        assert response.status_code == 428, f"Expected 428, got {response.status_code}: {response.text}"
        data = response.json()
        assert "requires_approval" in str(data) or "approval" in str(data).lower()
        print(f"✓ Direct status change correctly blocked with 428")
        
        # Cleanup
        self.__class__.direct_change_task_id = task_id
    
    # ==================== Cleanup Tests ====================
    
    def test_99_cleanup_test_data(self):
        """Cleanup test-created data"""
        self.authenticate()
        
        # Delete test tasks
        task_ids = [
            getattr(self.__class__, 'test_task_id', None),
            getattr(self.__class__, 'reject_task_id', None),
            getattr(self.__class__, 'direct_change_task_id', None)
        ]
        for task_id in task_ids:
            if task_id:
                try:
                    self.session.delete(f"{BASE_URL}/api/tasks/{task_id}")
                except:
                    pass
        
        # Delete test workflow rule
        rule_id = getattr(self.__class__, 'test_rule_id', None)
        workflow_id = getattr(self.__class__, 'test_workflow_id', None)
        if rule_id and workflow_id:
            try:
                self.session.delete(f"{BASE_URL}/api/workflows/{workflow_id}/rules/{rule_id}")
            except:
                pass
        
        # Delete test workflow
        if workflow_id:
            try:
                self.session.delete(f"{BASE_URL}/api/workflows/{workflow_id}")
            except:
                pass
        
        print("✓ Cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
