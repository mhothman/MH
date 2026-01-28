"""
Test Document Approval Workflows Feature
Tests for:
- Document Workflow CRUD
- Workflow Rule CRUD
- Document Status Change with Approval Enforcement
- Approval Request and Actions
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "test@proflow.com"
SUPER_ADMIN_PASSWORD = "test123456"
PROJECT_MANAGER_EMAIL = "mahmoud@eduflow.work"
PROJECT_MANAGER_PASSWORD = "test123456"
ORG_ID = "org_3a0711d3f937"


class TestDocumentWorkflowAuth:
    """Authentication tests for document workflow endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for super admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("access_token")
    
    def test_login_super_admin(self, auth_token):
        """Test super admin can login"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"✓ Super admin login successful")


class TestDocumentWorkflowCRUD:
    """Test Document Workflow CRUD operations"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for super admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def test_workflow_id(self, auth_headers):
        """Create a test workflow and return its ID"""
        workflow_data = {
            "name": f"TEST_Workflow_{datetime.now().strftime('%H%M%S')}",
            "description": "Test workflow for automated testing",
            "scope": "selective",
            "document_types": ["policy", "contract"],
            "project_ids": []
        }
        response = requests.post(
            f"{BASE_URL}/api/documents/workflows/?org_id={ORG_ID}",
            json=workflow_data,
            headers=auth_headers
        )
        if response.status_code == 200:
            return response.json().get("workflow_id")
        return None
    
    def test_list_document_workflows(self, auth_headers):
        """Test listing document workflows"""
        response = requests.get(
            f"{BASE_URL}/api/documents/workflows/?org_id={ORG_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to list workflows: {response.text}"
        workflows = response.json()
        assert isinstance(workflows, list)
        print(f"✓ Listed {len(workflows)} document workflows")
    
    def test_create_document_workflow(self, auth_headers):
        """Test creating a new document workflow"""
        workflow_data = {
            "name": f"TEST_Create_Workflow_{datetime.now().strftime('%H%M%S')}",
            "description": "Test workflow creation",
            "scope": "selective",
            "document_types": ["procedure"],
            "project_ids": []
        }
        response = requests.post(
            f"{BASE_URL}/api/documents/workflows/?org_id={ORG_ID}",
            json=workflow_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to create workflow: {response.text}"
        workflow = response.json()
        assert "workflow_id" in workflow
        assert workflow["name"] == workflow_data["name"]
        assert workflow["scope"] == "selective"
        print(f"✓ Created workflow: {workflow['workflow_id']}")
        
        # Cleanup - delete the test workflow
        requests.delete(
            f"{BASE_URL}/api/documents/workflows/{workflow['workflow_id']}",
            headers=auth_headers
        )
    
    def test_get_document_workflow_by_id(self, auth_headers):
        """Test getting a specific workflow by ID"""
        # First get list to find an existing workflow
        list_response = requests.get(
            f"{BASE_URL}/api/documents/workflows/?org_id={ORG_ID}",
            headers=auth_headers
        )
        workflows = list_response.json()
        
        if len(workflows) > 0:
            workflow_id = workflows[0]["workflow_id"]
            response = requests.get(
                f"{BASE_URL}/api/documents/workflows/{workflow_id}",
                headers=auth_headers
            )
            assert response.status_code == 200, f"Failed to get workflow: {response.text}"
            workflow = response.json()
            assert workflow["workflow_id"] == workflow_id
            assert "rules" in workflow  # Should include rules
            print(f"✓ Got workflow {workflow_id} with {len(workflow.get('rules', []))} rules")
        else:
            pytest.skip("No workflows available to test")
    
    def test_update_document_workflow(self, auth_headers, test_workflow_id):
        """Test updating a document workflow"""
        if not test_workflow_id:
            pytest.skip("No test workflow created")
        
        update_data = {
            "description": "Updated description for testing",
            "active": True
        }
        response = requests.put(
            f"{BASE_URL}/api/documents/workflows/{test_workflow_id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to update workflow: {response.text}"
        updated = response.json()
        assert updated["description"] == update_data["description"]
        print(f"✓ Updated workflow {test_workflow_id}")
    
    def test_delete_document_workflow(self, auth_headers):
        """Test deleting a document workflow"""
        # Create a workflow to delete
        workflow_data = {
            "name": f"TEST_Delete_Workflow_{datetime.now().strftime('%H%M%S')}",
            "description": "Workflow to be deleted",
            "scope": "selective",
            "document_types": [],
            "project_ids": []
        }
        create_response = requests.post(
            f"{BASE_URL}/api/documents/workflows/?org_id={ORG_ID}",
            json=workflow_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        workflow_id = create_response.json()["workflow_id"]
        
        # Delete the workflow
        delete_response = requests.delete(
            f"{BASE_URL}/api/documents/workflows/{workflow_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200, f"Failed to delete workflow: {delete_response.text}"
        print(f"✓ Deleted workflow {workflow_id}")
        
        # Verify deletion
        get_response = requests.get(
            f"{BASE_URL}/api/documents/workflows/{workflow_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404


class TestDocumentWorkflowRules:
    """Test Document Workflow Rule CRUD operations"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for super admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def test_workflow(self, auth_headers):
        """Create a test workflow for rule testing"""
        workflow_data = {
            "name": f"TEST_Rule_Workflow_{datetime.now().strftime('%H%M%S')}",
            "description": "Workflow for rule testing",
            "scope": "selective",
            "document_types": ["policy"],
            "project_ids": []
        }
        response = requests.post(
            f"{BASE_URL}/api/documents/workflows/?org_id={ORG_ID}",
            json=workflow_data,
            headers=auth_headers
        )
        if response.status_code == 200:
            yield response.json()
            # Cleanup
            requests.delete(
                f"{BASE_URL}/api/documents/workflows/{response.json()['workflow_id']}",
                headers=auth_headers
            )
        else:
            yield None
    
    def test_create_workflow_rule(self, auth_headers, test_workflow):
        """Test creating a workflow rule"""
        if not test_workflow:
            pytest.skip("No test workflow available")
        
        rule_data = {
            "from_status": "draft",
            "to_status": "published",
            "description": "Require approval for draft to published",
            "approval_required": True,
            "approval_type": "single",
            "approver_role": "org_admin",
            "notify_on_request": True,
            "notify_on_resolution": True,
            "pause_sla": True
        }
        response = requests.post(
            f"{BASE_URL}/api/documents/workflows/{test_workflow['workflow_id']}/rules",
            json=rule_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to create rule: {response.text}"
        rule = response.json()
        assert "rule_id" in rule
        assert rule["from_status"] == "draft"
        assert rule["to_status"] == "published"
        assert rule["approval_required"] == True
        print(f"✓ Created rule: {rule['rule_id']} (draft → published)")
    
    def test_list_workflow_rules(self, auth_headers, test_workflow):
        """Test listing rules for a workflow"""
        if not test_workflow:
            pytest.skip("No test workflow available")
        
        response = requests.get(
            f"{BASE_URL}/api/documents/workflows/{test_workflow['workflow_id']}/rules",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to list rules: {response.text}"
        rules = response.json()
        assert isinstance(rules, list)
        print(f"✓ Listed {len(rules)} rules for workflow")
    
    def test_duplicate_rule_prevention(self, auth_headers, test_workflow):
        """Test that duplicate rules are prevented"""
        if not test_workflow:
            pytest.skip("No test workflow available")
        
        # Create first rule
        rule_data = {
            "from_status": "in_review",
            "to_status": "approved",
            "approval_required": True,
            "approval_type": "single",
            "approver_role": "org_admin"
        }
        first_response = requests.post(
            f"{BASE_URL}/api/documents/workflows/{test_workflow['workflow_id']}/rules",
            json=rule_data,
            headers=auth_headers
        )
        
        if first_response.status_code == 200:
            # Try to create duplicate
            duplicate_response = requests.post(
                f"{BASE_URL}/api/documents/workflows/{test_workflow['workflow_id']}/rules",
                json=rule_data,
                headers=auth_headers
            )
            assert duplicate_response.status_code == 400, "Duplicate rule should be rejected"
            print(f"✓ Duplicate rule correctly rejected")
        else:
            # Rule might already exist
            print(f"✓ Rule creation handled (may already exist)")


class TestDocumentStatusChange:
    """Test document status change with approval enforcement"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for super admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_check_approval_required(self, auth_headers):
        """Test checking if approval is required for status change"""
        # Get a document first
        response = requests.get(
            f"{BASE_URL}/api/documents/?org_id={ORG_ID}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            documents = response.json()
            if len(documents) > 0:
                doc_id = documents[0]["document_id"]
                current_status = documents[0]["status"]
                
                # Check approval for a status change
                target_status = "published" if current_status != "published" else "archived"
                check_response = requests.get(
                    f"{BASE_URL}/api/documents/{doc_id}/check-approval?target_status={target_status}",
                    headers=auth_headers
                )
                assert check_response.status_code == 200, f"Failed to check approval: {check_response.text}"
                result = check_response.json()
                assert "requires_approval" in result
                assert "current_status" in result
                assert "target_status" in result
                print(f"✓ Checked approval for {current_status} → {target_status}: requires_approval={result['requires_approval']}")
            else:
                pytest.skip("No documents available")
        else:
            pytest.skip("Could not fetch documents")
    
    def test_get_document_approval_summary(self, auth_headers):
        """Test getting approval summary for a document"""
        # Get a document first
        response = requests.get(
            f"{BASE_URL}/api/documents/?org_id={ORG_ID}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            documents = response.json()
            if len(documents) > 0:
                doc_id = documents[0]["document_id"]
                
                summary_response = requests.get(
                    f"{BASE_URL}/api/documents/{doc_id}/approval-summary",
                    headers=auth_headers
                )
                assert summary_response.status_code == 200, f"Failed to get summary: {summary_response.text}"
                summary = summary_response.json()
                # Summary contains workflow info, not document_id directly
                assert "applicable_workflow" in summary or "has_pending_approval" in summary
                print(f"✓ Got approval summary for document {doc_id}")
            else:
                pytest.skip("No documents available")
        else:
            pytest.skip("Could not fetch documents")


class TestDocumentCRUD:
    """Test Document CRUD operations"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for super admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_list_documents(self, auth_headers):
        """Test listing documents"""
        response = requests.get(
            f"{BASE_URL}/api/documents/?org_id={ORG_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to list documents: {response.text}"
        documents = response.json()
        assert isinstance(documents, list)
        print(f"✓ Listed {len(documents)} documents")
    
    def test_get_document_types(self, auth_headers):
        """Test getting document types"""
        response = requests.get(
            f"{BASE_URL}/api/documents/types",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get types: {response.text}"
        types = response.json()
        assert isinstance(types, list)
        assert len(types) > 0
        # Verify expected types exist
        type_values = [t["value"] for t in types]
        assert "policy" in type_values
        assert "contract" in type_values
        print(f"✓ Got {len(types)} document types")
    
    def test_get_document_statuses(self, auth_headers):
        """Test getting document statuses"""
        response = requests.get(
            f"{BASE_URL}/api/documents/statuses",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get statuses: {response.text}"
        statuses = response.json()
        assert isinstance(statuses, list)
        assert len(statuses) > 0
        # Verify expected statuses exist
        status_values = [s["value"] for s in statuses]
        assert "draft" in status_values
        assert "published" in status_values
        assert "approved" in status_values
        print(f"✓ Got {len(statuses)} document statuses")
    
    def test_create_document(self, auth_headers):
        """Test creating a document"""
        doc_data = {
            "title": f"TEST_Document_{datetime.now().strftime('%H%M%S')}",
            "description": "Test document for automated testing",
            "document_type": "policy",
            "content": "This is test content",
            "tags": ["test", "automated"]
        }
        response = requests.post(
            f"{BASE_URL}/api/documents/?org_id={ORG_ID}",
            json=doc_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to create document: {response.text}"
        document = response.json()
        assert "document_id" in document
        assert document["title"] == doc_data["title"]
        assert document["status"] == "draft"  # Default status
        print(f"✓ Created document: {document['document_id']}")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/documents/{document['document_id']}",
            headers=auth_headers
        )
    
    def test_get_document_by_id(self, auth_headers):
        """Test getting a document by ID"""
        # Get list first
        list_response = requests.get(
            f"{BASE_URL}/api/documents/?org_id={ORG_ID}",
            headers=auth_headers
        )
        documents = list_response.json()
        
        if len(documents) > 0:
            doc_id = documents[0]["document_id"]
            response = requests.get(
                f"{BASE_URL}/api/documents/{doc_id}",
                headers=auth_headers
            )
            assert response.status_code == 200, f"Failed to get document: {response.text}"
            document = response.json()
            assert document["document_id"] == doc_id
            assert "title" in document
            assert "status" in document
            print(f"✓ Got document {doc_id}: {document['title']}")
        else:
            pytest.skip("No documents available")


class TestPendingApprovals:
    """Test pending approvals endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for super admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_get_pending_approvals(self, auth_headers):
        """Test getting pending document approvals"""
        response = requests.get(
            f"{BASE_URL}/api/documents/workflows/pending?org_id={ORG_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get pending approvals: {response.text}"
        approvals = response.json()
        assert isinstance(approvals, list)
        print(f"✓ Got {len(approvals)} pending approvals")
    
    def test_get_org_approvals(self, auth_headers):
        """Test getting all org document approvals"""
        response = requests.get(
            f"{BASE_URL}/api/documents/org/{ORG_ID}/approvals",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get org approvals: {response.text}"
        approvals = response.json()
        assert isinstance(approvals, list)
        print(f"✓ Got {len(approvals)} org approvals")


class TestWorkflowScopes:
    """Test workflow scope functionality"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for super admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_selective_workflow_with_document_types(self, auth_headers):
        """Test creating selective workflow with document types filter"""
        workflow_data = {
            "name": f"TEST_Selective_Types_{datetime.now().strftime('%H%M%S')}",
            "description": "Selective workflow for specific document types",
            "scope": "selective",
            "document_types": ["contract", "policy"],
            "project_ids": []
        }
        response = requests.post(
            f"{BASE_URL}/api/documents/workflows/?org_id={ORG_ID}",
            json=workflow_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to create selective workflow: {response.text}"
        workflow = response.json()
        assert workflow["scope"] == "selective"
        assert "contract" in workflow["document_types"]
        assert "policy" in workflow["document_types"]
        print(f"✓ Created selective workflow with document types filter")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/documents/workflows/{workflow['workflow_id']}",
            headers=auth_headers
        )
    
    def test_global_workflow_uniqueness(self, auth_headers):
        """Test that only one global workflow can exist"""
        # Check if global workflow already exists
        list_response = requests.get(
            f"{BASE_URL}/api/documents/workflows/?org_id={ORG_ID}",
            headers=auth_headers
        )
        workflows = list_response.json()
        has_global = any(w.get("scope") == "global" for w in workflows)
        
        if has_global:
            # Try to create another global workflow - should fail
            workflow_data = {
                "name": f"TEST_Global_Duplicate_{datetime.now().strftime('%H%M%S')}",
                "description": "Duplicate global workflow",
                "scope": "global",
                "document_types": [],
                "project_ids": []
            }
            response = requests.post(
                f"{BASE_URL}/api/documents/workflows/?org_id={ORG_ID}",
                json=workflow_data,
                headers=auth_headers
            )
            assert response.status_code == 400, "Should not allow duplicate global workflow"
            print(f"✓ Duplicate global workflow correctly rejected")
        else:
            print(f"✓ No global workflow exists - uniqueness test skipped")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
