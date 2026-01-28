"""
Test Documents Page Features
Tests for:
- Documents Page UI API endpoints
- Document Detail Dialog APIs
- Document Status Change with Approval
- Email notification methods for document approvals
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "test@proflow.com"
SUPER_ADMIN_PASSWORD = "test123456"
ORG_ID = "org_3a0711d3f937"
EXISTING_DOC_ID = "doc_7de8abf5caf9"


class TestDocumentsPageAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for super admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_login_success(self, auth_headers):
        """Test super admin can login"""
        assert "Authorization" in auth_headers
        print("✓ Super admin login successful")


class TestDocumentsPageList:
    """Test Documents Page list functionality"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_list_documents_for_org(self, auth_headers):
        """Test listing documents for organization"""
        response = requests.get(
            f"{BASE_URL}/api/documents/?org_id={ORG_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        documents = response.json()
        assert isinstance(documents, list)
        print(f"✓ Listed {len(documents)} documents for org")
        
        # Verify document structure
        if documents:
            doc = documents[0]
            assert "document_id" in doc
            assert "title" in doc
            assert "status" in doc
            assert "document_type" in doc
            print(f"✓ Document structure verified: {doc['title']}")
    
    def test_get_document_types(self, auth_headers):
        """Test getting document types for filter dropdown"""
        response = requests.get(
            f"{BASE_URL}/api/documents/types",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        types = response.json()
        assert isinstance(types, list)
        assert len(types) >= 8  # policy, procedure, specification, contract, report, proposal, template, other
        
        type_values = [t["value"] for t in types]
        assert "policy" in type_values
        assert "contract" in type_values
        assert "procedure" in type_values
        print(f"✓ Got {len(types)} document types for filter")
    
    def test_get_document_statuses(self, auth_headers):
        """Test getting document statuses for filter dropdown"""
        response = requests.get(
            f"{BASE_URL}/api/documents/statuses",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        statuses = response.json()
        assert isinstance(statuses, list)
        
        status_values = [s["value"] for s in statuses]
        assert "draft" in status_values
        assert "published" in status_values
        assert "approved" in status_values
        assert "pending_approval" in status_values
        print(f"✓ Got {len(statuses)} document statuses for filter")


class TestDocumentDetailDialog:
    """Test Document Detail Dialog functionality"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_get_document_details(self, auth_headers):
        """Test getting document details for dialog"""
        response = requests.get(
            f"{BASE_URL}/api/documents/{EXISTING_DOC_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        doc = response.json()
        
        # Verify all fields needed for Details tab
        assert "document_id" in doc
        assert "title" in doc
        assert "description" in doc
        assert "document_type" in doc
        assert "status" in doc
        assert "owner_id" in doc
        assert "created_at" in doc
        assert "updated_at" in doc
        print(f"✓ Got document details: {doc['title']}")
    
    def test_get_document_approval_summary(self, auth_headers):
        """Test getting approval summary for Approval tab"""
        response = requests.get(
            f"{BASE_URL}/api/documents/{EXISTING_DOC_ID}/approval-summary",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        summary = response.json()
        
        # Verify approval summary structure
        assert "has_pending_approval" in summary or "pending_approval" in summary
        assert "approval_history" in summary or "applicable_workflow" in summary
        print(f"✓ Got approval summary for document")
    
    def test_check_approval_required_for_status_change(self, auth_headers):
        """Test checking if approval is required for status change"""
        # Get current document status first
        doc_response = requests.get(
            f"{BASE_URL}/api/documents/{EXISTING_DOC_ID}",
            headers=auth_headers
        )
        current_status = doc_response.json().get("status", "draft")
        
        # Check approval for a different status
        target_status = "archived" if current_status != "archived" else "draft"
        
        response = requests.get(
            f"{BASE_URL}/api/documents/{EXISTING_DOC_ID}/check-approval?target_status={target_status}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        result = response.json()
        
        assert "requires_approval" in result
        assert "current_status" in result
        assert "target_status" in result
        print(f"✓ Checked approval for {current_status} → {target_status}: requires={result['requires_approval']}")


class TestDocumentCRUD:
    """Test Document CRUD operations for Documents Page"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_create_document(self, auth_headers):
        """Test creating a new document via New Document dialog"""
        doc_data = {
            "title": f"TEST_UI_Document_{datetime.now().strftime('%H%M%S')}",
            "description": "Test document created via Documents Page UI",
            "document_type": "procedure",
            "tags": ["test", "ui", "automated"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documents/?org_id={ORG_ID}",
            json=doc_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        doc = response.json()
        
        assert doc["title"] == doc_data["title"]
        assert doc["description"] == doc_data["description"]
        assert doc["document_type"] == "procedure"
        assert doc["status"] == "draft"  # Default status
        assert "test" in doc.get("tags", [])
        print(f"✓ Created document: {doc['document_id']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/documents/{doc['document_id']}", headers=auth_headers)
    
    def test_update_document(self, auth_headers):
        """Test updating a document via Edit dialog"""
        # Create a test document first
        create_response = requests.post(
            f"{BASE_URL}/api/documents/?org_id={ORG_ID}",
            json={
                "title": f"TEST_Update_Doc_{datetime.now().strftime('%H%M%S')}",
                "description": "Original description",
                "document_type": "policy"
            },
            headers=auth_headers
        )
        doc_id = create_response.json()["document_id"]
        
        # Update the document
        update_data = {
            "title": "Updated Title",
            "description": "Updated description",
            "tags": ["updated", "test"]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/documents/{doc_id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        updated = response.json()
        
        assert updated["title"] == "Updated Title"
        assert updated["description"] == "Updated description"
        print(f"✓ Updated document: {doc_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/documents/{doc_id}", headers=auth_headers)
    
    def test_delete_document(self, auth_headers):
        """Test deleting a document via Delete action"""
        # Create a test document first
        create_response = requests.post(
            f"{BASE_URL}/api/documents/?org_id={ORG_ID}",
            json={
                "title": f"TEST_Delete_Doc_{datetime.now().strftime('%H%M%S')}",
                "document_type": "other"
            },
            headers=auth_headers
        )
        doc_id = create_response.json()["document_id"]
        
        # Delete the document
        response = requests.delete(
            f"{BASE_URL}/api/documents/{doc_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print(f"✓ Deleted document: {doc_id}")
        
        # Verify deletion
        get_response = requests.get(
            f"{BASE_URL}/api/documents/{doc_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
        print(f"✓ Verified document deleted (404)")


class TestDocumentStatusChange:
    """Test Document Status Change functionality"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_change_document_status_no_approval(self, auth_headers):
        """Test changing document status when no approval required"""
        # Create a test document
        create_response = requests.post(
            f"{BASE_URL}/api/documents/?org_id={ORG_ID}",
            json={
                "title": f"TEST_Status_Change_{datetime.now().strftime('%H%M%S')}",
                "document_type": "other"  # Use 'other' type which may not have workflow
            },
            headers=auth_headers
        )
        doc = create_response.json()
        doc_id = doc["document_id"]
        
        # Try to change status
        response = requests.post(
            f"{BASE_URL}/api/documents/{doc_id}/change-status",
            json={
                "target_status": "in_review",
                "comment": "Moving to review"
            },
            headers=auth_headers
        )
        
        # Status change should work (either directly or create approval request)
        assert response.status_code in [200, 201], f"Failed: {response.text}"
        result = response.json()
        
        if result.get("status") == "changed":
            print(f"✓ Status changed directly (no approval required)")
        elif result.get("status") == "approval_required":
            print(f"✓ Approval request created")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/documents/{doc_id}", headers=auth_headers)


class TestPendingApprovals:
    """Test Pending Approvals functionality"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_get_pending_approvals_for_user(self, auth_headers):
        """Test getting pending approvals for current user"""
        response = requests.get(
            f"{BASE_URL}/api/documents/workflows/pending?org_id={ORG_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        approvals = response.json()
        assert isinstance(approvals, list)
        print(f"✓ Got {len(approvals)} pending approvals for user")
    
    def test_get_org_approvals(self, auth_headers):
        """Test getting all org document approvals"""
        response = requests.get(
            f"{BASE_URL}/api/documents/org/{ORG_ID}/approvals",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        approvals = response.json()
        assert isinstance(approvals, list)
        print(f"✓ Got {len(approvals)} org approvals")


class TestEmailNotificationMethods:
    """Test email notification methods exist and are callable"""
    
    def test_email_service_methods_exist(self):
        """Verify email service has document approval methods"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from services.email_service import email_service
            
            # Check methods exist
            assert hasattr(email_service, 'send_document_approval_requested'), \
                "Missing send_document_approval_requested method"
            assert hasattr(email_service, 'send_document_approval_approved'), \
                "Missing send_document_approval_approved method"
            assert hasattr(email_service, 'send_document_approval_rejected'), \
                "Missing send_document_approval_rejected method"
            
            print("✓ Email service has all document approval methods")
            
            # Verify methods are async
            import inspect
            assert inspect.iscoroutinefunction(email_service.send_document_approval_requested), \
                "send_document_approval_requested should be async"
            assert inspect.iscoroutinefunction(email_service.send_document_approval_approved), \
                "send_document_approval_approved should be async"
            assert inspect.iscoroutinefunction(email_service.send_document_approval_rejected), \
                "send_document_approval_rejected should be async"
            
            print("✓ All email methods are async")
            
        except ImportError as e:
            pytest.skip(f"Could not import email_service: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
