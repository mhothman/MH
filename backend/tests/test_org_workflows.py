"""
Test Organization-Level Workflow CRUD and Approval System
Tests the refactored workflow feature with global/selective scopes
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Test credentials
ADMIN_EMAIL = "test@proflow.com"
ADMIN_PASSWORD = "test123456"


@pytest.fixture(scope="module")
def auth_session():
    """Login and return authenticated session with org/project info"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    token = data.get("access_token") or data.get("token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # Get org_id (use trailing slash to avoid redirect issues)
    response = session.get(f"{BASE_URL}/api/organizations/")
    assert response.status_code == 200, f"Failed to get orgs: {response.text}"
    orgs = response.json()
    assert len(orgs) > 0, "No organizations found"
    org_id = orgs[0]["org_id"]
    
    # Get project_id (use trailing slash)
    response = session.get(f"{BASE_URL}/api/projects/")
    assert response.status_code == 200, f"Failed to get projects: {response.text}"
    projects = response.json()
    project_id = None
    for p in projects:
        if p.get("org_id") == org_id and p.get("status") == "active":
            project_id = p["project_id"]
            break
    # Fallback to any project in org
    if not project_id:
        for p in projects:
            if p.get("org_id") == org_id:
                project_id = p["project_id"]
                break
    assert project_id, "No project found in org"
    
    return {
        "session": session,
        "user_id": data["user"]["user_id"],
        "org_id": org_id,
        "project_id": project_id
    }


class TestOrgWorkflowCRUD:
    """Test Organization-level Workflow CRUD operations"""
    
    def test_01_list_org_workflows_initial(self, auth_session):
        """List workflows for organization"""
        session = auth_session["session"]
        org_id = auth_session["org_id"]
        
        response = session.get(f"{BASE_URL}/api/workflows/org/{org_id}")
        assert response.status_code == 200, f"Failed to list workflows: {response.text}"
        workflows = response.json()
        assert isinstance(workflows, list)
        
        # Store existing global workflow if any
        for wf in workflows:
            if wf.get("scope") == "global" and wf.get("active"):
                auth_session["existing_global_workflow_id"] = wf["workflow_id"]
                break
        
        print(f"✓ Listed {len(workflows)} existing workflows")
    
    def test_02_create_or_use_global_workflow(self, auth_session):
        """Create a global workflow or use existing one"""
        session = auth_session["session"]
        org_id = auth_session["org_id"]
        
        # Check if global workflow already exists
        if auth_session.get("existing_global_workflow_id"):
            auth_session["global_workflow_id"] = auth_session["existing_global_workflow_id"]
            print(f"✓ Using existing global workflow: {auth_session['global_workflow_id']}")
            return
        
        workflow_name = f"TEST_Global_Workflow_{uuid.uuid4().hex[:6]}"
        response = session.post(
            f"{BASE_URL}/api/workflows/org/{org_id}",
            json={
                "name": workflow_name,
                "description": "Test global workflow for all projects",
                "scope": "global",
                "active": True
            }
        )
        
        if response.status_code == 400 and "global workflow already exists" in response.text.lower():
            # Get the existing global workflow
            response = session.get(f"{BASE_URL}/api/workflows/org/{org_id}")
            workflows = response.json()
            for wf in workflows:
                if wf.get("scope") == "global" and wf.get("active"):
                    auth_session["global_workflow_id"] = wf["workflow_id"]
                    print(f"✓ Using existing global workflow: {wf['workflow_id']}")
                    return
        
        assert response.status_code == 200, f"Failed to create global workflow: {response.text}"
        workflow = response.json()
        auth_session["global_workflow_id"] = workflow["workflow_id"]
        auth_session["created_global_workflow"] = True
        print(f"✓ Created global workflow: {workflow['workflow_id']}")
    
    def test_03_prevent_duplicate_global_workflow(self, auth_session):
        """Verify that creating a second active global workflow is prevented"""
        session = auth_session["session"]
        org_id = auth_session["org_id"]
        
        response = session.post(
            f"{BASE_URL}/api/workflows/org/{org_id}",
            json={
                "name": "TEST_Second_Global",
                "description": "Should fail",
                "scope": "global",
                "active": True
            }
        )
        # Should fail with 400
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "global workflow already exists" in response.text.lower()
        print("✓ Correctly prevented duplicate global workflow")
    
    def test_04_create_selective_workflow(self, auth_session):
        """Create a selective workflow (applies to specific projects)"""
        session = auth_session["session"]
        org_id = auth_session["org_id"]
        
        workflow_name = f"TEST_Selective_Workflow_{uuid.uuid4().hex[:6]}"
        response = session.post(
            f"{BASE_URL}/api/workflows/org/{org_id}",
            json={
                "name": workflow_name,
                "description": "Test selective workflow for specific projects",
                "scope": "selective",
                "active": True
            }
        )
        assert response.status_code == 200, f"Failed to create selective workflow: {response.text}"
        workflow = response.json()
        assert workflow["name"] == workflow_name
        assert workflow["scope"] == "selective"
        auth_session["selective_workflow_id"] = workflow["workflow_id"]
        print(f"✓ Created selective workflow: {workflow['workflow_id']}")
    
    def test_05_get_workflow_by_id(self, auth_session):
        """Get workflow details by ID"""
        session = auth_session["session"]
        workflow_id = auth_session.get("global_workflow_id")
        if not workflow_id:
            pytest.skip("No global workflow available")
        
        response = session.get(f"{BASE_URL}/api/workflows/{workflow_id}")
        assert response.status_code == 200, f"Failed to get workflow: {response.text}"
        workflow = response.json()
        assert workflow["workflow_id"] == workflow_id
        assert workflow["scope"] == "global"
        assert "rules" in workflow  # Should include rules array
        print(f"✓ Got workflow details with {len(workflow.get('rules', []))} rules")
    
    def test_06_update_workflow(self, auth_session):
        """Update workflow properties"""
        session = auth_session["session"]
        workflow_id = auth_session.get("selective_workflow_id")
        if not workflow_id:
            pytest.skip("No selective workflow created")
        
        response = session.put(
            f"{BASE_URL}/api/workflows/{workflow_id}",
            json={
                "name": "TEST_Updated_Selective_Workflow",
                "description": "Updated description"
            }
        )
        assert response.status_code == 200, f"Failed to update workflow: {response.text}"
        workflow = response.json()
        assert workflow["name"] == "TEST_Updated_Selective_Workflow"
        print("✓ Updated workflow successfully")


class TestWorkflowRules:
    """Test Workflow Rule CRUD operations"""
    
    def test_07_create_rule_todo_to_done(self, auth_session):
        """Create a rule requiring approval for todo -> done transition"""
        session = auth_session["session"]
        workflow_id = auth_session.get("global_workflow_id")
        if not workflow_id:
            pytest.skip("No global workflow available")
        
        # First check if rule already exists
        response = session.get(f"{BASE_URL}/api/workflows/{workflow_id}/rules")
        if response.status_code == 200:
            rules = response.json()
            for rule in rules:
                if rule["from_status"] == "todo" and rule["to_status"] == "done":
                    auth_session["rule_id"] = rule["rule_id"]
                    print(f"✓ Using existing rule: {rule['rule_id']}")
                    return
        
        response = session.post(
            f"{BASE_URL}/api/workflows/{workflow_id}/rules",
            json={
                "from_status": "todo",
                "to_status": "done",
                "approval_required": True,
                "approval_type": "single",
                "approver_role": "org_admin",
                "notify_on_request": True,
                "notify_on_resolution": True
            }
        )
        
        if response.status_code == 400 and "already exists" in response.text.lower():
            # Get existing rule
            response = session.get(f"{BASE_URL}/api/workflows/{workflow_id}/rules")
            rules = response.json()
            for rule in rules:
                if rule["from_status"] == "todo" and rule["to_status"] == "done":
                    auth_session["rule_id"] = rule["rule_id"]
                    print(f"✓ Using existing rule: {rule['rule_id']}")
                    return
        
        assert response.status_code == 200, f"Failed to create rule: {response.text}"
        rule = response.json()
        auth_session["rule_id"] = rule["rule_id"]
        auth_session["created_rule"] = True
        print(f"✓ Created rule: todo -> done (requires approval)")
    
    def test_08_prevent_duplicate_rule(self, auth_session):
        """Verify duplicate rule creation is prevented"""
        session = auth_session["session"]
        workflow_id = auth_session.get("global_workflow_id")
        if not workflow_id:
            pytest.skip("No global workflow available")
        
        response = session.post(
            f"{BASE_URL}/api/workflows/{workflow_id}/rules",
            json={
                "from_status": "todo",
                "to_status": "done",
                "approval_required": True,
                "approval_type": "single",
                "approver_role": "project_manager"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "already exists" in response.text.lower()
        print("✓ Correctly prevented duplicate rule")
    
    def test_09_get_workflow_rules(self, auth_session):
        """Get all rules for a workflow"""
        session = auth_session["session"]
        workflow_id = auth_session.get("global_workflow_id")
        if not workflow_id:
            pytest.skip("No global workflow available")
        
        response = session.get(f"{BASE_URL}/api/workflows/{workflow_id}/rules")
        assert response.status_code == 200, f"Failed to get rules: {response.text}"
        rules = response.json()
        assert isinstance(rules, list)
        assert len(rules) >= 1
        print(f"✓ Got {len(rules)} rule(s) for workflow")
    
    def test_10_update_rule(self, auth_session):
        """Update a workflow rule"""
        session = auth_session["session"]
        rule_id = auth_session.get("rule_id")
        if not rule_id:
            pytest.skip("No rule available")
        
        response = session.put(
            f"{BASE_URL}/api/workflows/rules/{rule_id}",
            json={
                "approval_timeout_minutes": 60,
                "auto_approve_on_timeout": True
            }
        )
        assert response.status_code == 200, f"Failed to update rule: {response.text}"
        rule = response.json()
        assert rule["approval_timeout_minutes"] == 60
        assert rule["auto_approve_on_timeout"] == True
        print("✓ Updated rule successfully")


class TestProjectAssignment:
    """Test project assignment to selective workflows"""
    
    def test_11_assign_projects_to_selective_workflow(self, auth_session):
        """Assign projects to a selective workflow"""
        session = auth_session["session"]
        workflow_id = auth_session.get("selective_workflow_id")
        project_id = auth_session["project_id"]
        if not workflow_id:
            pytest.skip("No selective workflow created")
        
        response = session.put(
            f"{BASE_URL}/api/workflows/{workflow_id}/projects",
            json={"project_ids": [project_id]}
        )
        assert response.status_code == 200, f"Failed to assign projects: {response.text}"
        data = response.json()
        assert project_id in data.get("assigned_projects", [])
        print(f"✓ Assigned project to selective workflow")
    
    def test_12_get_workflow_projects(self, auth_session):
        """Get projects assigned to a workflow"""
        session = auth_session["session"]
        workflow_id = auth_session.get("selective_workflow_id")
        project_id = auth_session["project_id"]
        if not workflow_id:
            pytest.skip("No selective workflow created")
        
        response = session.get(f"{BASE_URL}/api/workflows/{workflow_id}/projects")
        assert response.status_code == 200, f"Failed to get projects: {response.text}"
        projects = response.json()
        assert isinstance(projects, list)
        project_ids = [p["project_id"] for p in projects]
        assert project_id in project_ids
        print(f"✓ Got {len(projects)} assigned project(s)")
    
    def test_13_cannot_assign_to_global_workflow(self, auth_session):
        """Verify that projects cannot be assigned to global workflows"""
        session = auth_session["session"]
        workflow_id = auth_session.get("global_workflow_id")
        project_id = auth_session["project_id"]
        if not workflow_id:
            pytest.skip("No global workflow available")
        
        response = session.put(
            f"{BASE_URL}/api/workflows/{workflow_id}/projects",
            json={"project_ids": [project_id]}
        )
        # Should fail - global workflows don't need project assignment
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ Correctly prevented project assignment to global workflow")


class TestWorkflowResolution:
    """Test workflow resolution logic (global takes priority)"""
    
    def test_14_get_applicable_workflows_for_project(self, auth_session):
        """Get workflows that apply to a project"""
        session = auth_session["session"]
        project_id = auth_session["project_id"]
        
        response = session.get(f"{BASE_URL}/api/workflows/projects/{project_id}/applicable")
        assert response.status_code == 200, f"Failed to get applicable workflows: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "project_id" in data
        assert "global_workflow" in data
        assert "selective_workflows" in data
        assert "effective_workflow" in data
        
        # Global workflow should be the effective one (takes priority)
        if data["global_workflow"]:
            assert data["effective_workflow"]["workflow_id"] == data["global_workflow"]["workflow_id"]
            print("✓ Global workflow correctly takes priority as effective workflow")
        else:
            print("✓ Got applicable workflows (no global, using selective)")


class TestApprovalFlow:
    """Test approval request and action flow"""
    
    def test_15_create_test_task(self, auth_session):
        """Create a test task for approval testing"""
        session = auth_session["session"]
        project_id = auth_session["project_id"]
        
        task_title = f"TEST_Approval_Task_{uuid.uuid4().hex[:6]}"
        response = session.post(
            f"{BASE_URL}/api/tasks/",  # Note trailing slash
            json={
                "title": task_title,
                "description": "Task for testing approval workflow",
                "project_id": project_id,
                "status": "todo",
                "priority": "medium"
            }
        )
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        task = response.json()
        auth_session["task_id"] = task["task_id"]
        print(f"✓ Created test task: {task['task_id']}")
    
    def test_16_check_approval_required(self, auth_session):
        """Check if approval is required for status change"""
        session = auth_session["session"]
        task_id = auth_session.get("task_id")
        if not task_id:
            pytest.skip("No task created")
        
        response = session.get(f"{BASE_URL}/api/workflows/tasks/{task_id}/check-approval?target_status=done")
        assert response.status_code == 200, f"Failed to check approval: {response.text}"
        data = response.json()
        assert "requires_approval" in data
        assert "current_status" in data
        assert "target_status" in data
        print(f"✓ Approval required: {data['requires_approval']}")
    
    def test_17_request_approval(self, auth_session):
        """Request approval for task status change"""
        session = auth_session["session"]
        task_id = auth_session.get("task_id")
        if not task_id:
            pytest.skip("No task created")
        
        response = session.post(
            f"{BASE_URL}/api/workflows/tasks/{task_id}/request-approval",
            json={
                "target_status": "done",
                "comment": "Test approval request"
            }
        )
        
        # If no approval required, that's also valid
        if response.status_code == 400 and "no approval required" in response.text.lower():
            print("✓ No approval required for this transition (no matching rule)")
            pytest.skip("No approval rule configured for this transition")
        
        assert response.status_code == 200, f"Failed to request approval: {response.text}"
        data = response.json()
        assert "approval" in data
        auth_session["approval_id"] = data["approval"]["approval_id"]
        print(f"✓ Created approval request: {auth_session['approval_id']}")
    
    def test_18_verify_task_locked(self, auth_session):
        """Verify task is locked while approval is pending"""
        session = auth_session["session"]
        task_id = auth_session.get("task_id")
        approval_id = auth_session.get("approval_id")
        if not task_id or not approval_id:
            pytest.skip("No task or approval created")
        
        response = session.get(f"{BASE_URL}/api/tasks/{task_id}")
        assert response.status_code == 200, f"Failed to get task: {response.text}"
        task = response.json()
        assert task.get("approval_locked") == True, "Task should be locked"
        print("✓ Task is correctly locked pending approval")
    
    def test_19_get_task_approval_summary(self, auth_session):
        """Get approval summary for task"""
        session = auth_session["session"]
        task_id = auth_session.get("task_id")
        approval_id = auth_session.get("approval_id")
        if not task_id or not approval_id:
            pytest.skip("No task or approval created")
        
        response = session.get(f"{BASE_URL}/api/workflows/tasks/{task_id}/approval-summary")
        assert response.status_code == 200, f"Failed to get summary: {response.text}"
        summary = response.json()
        assert summary["has_pending_approval"] == True
        assert summary["is_locked"] == True
        print("✓ Got task approval summary")
    
    def test_20_get_pending_approvals(self, auth_session):
        """Get pending approvals for user"""
        session = auth_session["session"]
        org_id = auth_session["org_id"]
        approval_id = auth_session.get("approval_id")
        if not approval_id:
            pytest.skip("No approval created")
        
        response = session.get(f"{BASE_URL}/api/workflows/pending?org_id={org_id}")
        assert response.status_code == 200, f"Failed to get pending: {response.text}"
        approvals = response.json()
        assert isinstance(approvals, list)
        # Should find our approval
        approval_ids = [a["approval_id"] for a in approvals]
        assert approval_id in approval_ids
        print(f"✓ Found {len(approvals)} pending approval(s)")
    
    def test_21_approve_request(self, auth_session):
        """Approve the approval request"""
        session = auth_session["session"]
        approval_id = auth_session.get("approval_id")
        if not approval_id:
            pytest.skip("No approval created")
        
        response = session.post(
            f"{BASE_URL}/api/workflows/approvals/{approval_id}/approve",
            json={
                "action": "approve",
                "comment": "Approved for testing"
            }
        )
        assert response.status_code == 200, f"Failed to approve: {response.text}"
        print("✓ Approved the request")
    
    def test_22_verify_task_status_changed(self, auth_session):
        """Verify task status changed after approval"""
        session = auth_session["session"]
        task_id = auth_session.get("task_id")
        approval_id = auth_session.get("approval_id")
        if not task_id or not approval_id:
            pytest.skip("No task or approval created")
        
        response = session.get(f"{BASE_URL}/api/tasks/{task_id}")
        assert response.status_code == 200, f"Failed to get task: {response.text}"
        task = response.json()
        assert task["status"] == "done", f"Expected 'done', got '{task['status']}'"
        assert task.get("approval_locked") == False, "Task should be unlocked"
        print("✓ Task status changed to 'done' after approval")


class TestRejectFlow:
    """Test approval rejection flow"""
    
    def test_23_create_task_for_rejection(self, auth_session):
        """Create another task for rejection testing"""
        session = auth_session["session"]
        project_id = auth_session["project_id"]
        
        task_title = f"TEST_Reject_Task_{uuid.uuid4().hex[:6]}"
        response = session.post(
            f"{BASE_URL}/api/tasks/",  # Note trailing slash
            json={
                "title": task_title,
                "description": "Task for testing rejection",
                "project_id": project_id,
                "status": "todo",
                "priority": "low"
            }
        )
        assert response.status_code in [200, 201], f"Failed to create task: {response.text}"
        task = response.json()
        auth_session["reject_task_id"] = task["task_id"]
        print(f"✓ Created task for rejection test: {task['task_id']}")
    
    def test_24_request_approval_for_rejection(self, auth_session):
        """Request approval that will be rejected"""
        session = auth_session["session"]
        task_id = auth_session.get("reject_task_id")
        if not task_id:
            pytest.skip("No reject task created")
        
        response = session.post(
            f"{BASE_URL}/api/workflows/tasks/{task_id}/request-approval",
            json={
                "target_status": "done",
                "comment": "This will be rejected"
            }
        )
        
        if response.status_code == 400 and "no approval required" in response.text.lower():
            print("✓ No approval required for this transition")
            pytest.skip("No approval rule configured")
        
        assert response.status_code == 200, f"Failed to request approval: {response.text}"
        data = response.json()
        auth_session["reject_approval_id"] = data["approval"]["approval_id"]
        print(f"✓ Created approval request for rejection")
    
    def test_25_reject_request(self, auth_session):
        """Reject the approval request"""
        session = auth_session["session"]
        approval_id = auth_session.get("reject_approval_id")
        if not approval_id:
            pytest.skip("No reject approval created")
        
        response = session.post(
            f"{BASE_URL}/api/workflows/approvals/{approval_id}/reject",
            json={
                "action": "reject",
                "comment": "Rejected for testing"
            }
        )
        assert response.status_code == 200, f"Failed to reject: {response.text}"
        print("✓ Rejected the request")
    
    def test_26_verify_task_unchanged_after_rejection(self, auth_session):
        """Verify task status unchanged after rejection"""
        session = auth_session["session"]
        task_id = auth_session.get("reject_task_id")
        approval_id = auth_session.get("reject_approval_id")
        if not task_id or not approval_id:
            pytest.skip("No reject task or approval created")
        
        response = session.get(f"{BASE_URL}/api/tasks/{task_id}")
        assert response.status_code == 200, f"Failed to get task: {response.text}"
        task = response.json()
        assert task["status"] == "todo", f"Expected 'todo', got '{task['status']}'"
        assert task.get("approval_locked") == False, "Task should be unlocked"
        print("✓ Task status unchanged after rejection")


class TestCleanup:
    """Cleanup test data"""
    
    def test_99_cleanup(self, auth_session):
        """Delete test workflows and tasks"""
        session = auth_session["session"]
        
        # Delete test tasks
        for task_key in ["task_id", "reject_task_id"]:
            if auth_session.get(task_key):
                session.delete(f"{BASE_URL}/api/tasks/{auth_session[task_key]}")
        
        # Delete test selective workflow (only if we created it)
        if auth_session.get("selective_workflow_id"):
            session.delete(f"{BASE_URL}/api/workflows/{auth_session['selective_workflow_id']}")
        
        # Only delete global workflow if we created it
        if auth_session.get("created_global_workflow") and auth_session.get("global_workflow_id"):
            session.delete(f"{BASE_URL}/api/workflows/{auth_session['global_workflow_id']}")
        
        # Only delete rule if we created it
        if auth_session.get("created_rule") and auth_session.get("rule_id"):
            session.delete(f"{BASE_URL}/api/workflows/rules/{auth_session['rule_id']}")
        
        print("✓ Cleaned up test data")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
