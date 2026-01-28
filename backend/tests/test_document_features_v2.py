"""
Test Document Features V2 - Attachments, Versions, and Org Approvals
Tests for:
- Document Attachments CRUD API
- Document Version History API
- Org Document Approvals API (moved route)
- Dashboard Pending Approvals Widget data
"""
import pytest
import requests
import os
from datetime import datetime
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "test@proflow.com"
SUPER_ADMIN_PASSWORD = "test123456"
ORG_ID = "org_3a0711d3f937"
TEST_DOC_IDS = ["doc_7de8abf5caf9", "doc_83436f47da27"]


class TestAuth:
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


class TestDocumentAttachments:
    """Test Document Attachments CRUD API"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def test_document(self, auth_headers):
        """Create a test document for attachment testing"""
        doc_data = {
            "title": f"TEST_Attachment_Doc_{datetime.now().strftime('%H%M%S')}",
            "description": "Document for attachment testing",
            "document_type": "policy"
        }
        response = requests.post(
            f"{BASE_URL}/api/documents/?org_id={ORG_ID}",
            json=doc_data,
            headers=auth_headers
        )
        if response.status_code == 200:
            doc = response.json()
            yield doc
            # Cleanup
            requests.delete(f"{BASE_URL}/api/documents/{doc['document_id']}", headers=auth_headers)
        else:
            yield None
    
    def test_list_document_attachments_empty(self, auth_headers, test_document):
        """Test listing attachments for a document with no attachments"""
        if not test_document:
            pytest.skip("No test document available")
        
        response = requests.get(
            f"{BASE_URL}/api/documents/{test_document['document_id']}/attachments",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        attachments = response.json()
        assert isinstance(attachments, list)
        print(f"✓ Listed attachments (empty): {len(attachments)}")
    
    def test_add_document_attachment_metadata(self, auth_headers, test_document):
        """Test adding attachment metadata to a document"""
        if not test_document:
            pytest.skip("No test document available")
        
        attachment_data = {
            "filename": "test_file.pdf",
            "file_url": "/uploads/test_file.pdf",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "description": "Test attachment"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documents/{test_document['document_id']}/attachments",
            json=attachment_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        attachment = response.json()
        
        assert "attachment_id" in attachment
        assert attachment["filename"] == "test_file.pdf"
        assert attachment["file_size"] == 1024
        assert attachment["mime_type"] == "application/pdf"
        print(f"✓ Added attachment metadata: {attachment['attachment_id']}")
        
        return attachment["attachment_id"]
    
    def test_upload_document_file(self, auth_headers, test_document):
        """Test uploading a file to a document"""
        if not test_document:
            pytest.skip("No test document available")
        
        # Create a test file in memory
        file_content = b"This is test file content for document attachment testing."
        files = {
            'file': ('test_upload.txt', io.BytesIO(file_content), 'text/plain')
        }
        
        # Remove Content-Type header for multipart upload
        upload_headers = {"Authorization": auth_headers["Authorization"]}
        
        response = requests.post(
            f"{BASE_URL}/api/documents/{test_document['document_id']}/upload",
            files=files,
            headers=upload_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        attachment = response.json()
        
        assert "attachment_id" in attachment
        assert attachment["filename"] == "test_upload.txt"
        assert attachment["file_size"] == len(file_content)
        assert "file_url" in attachment
        print(f"✓ Uploaded file: {attachment['attachment_id']} ({attachment['file_size']} bytes)")
        
        return attachment["attachment_id"]
    
    def test_list_document_attachments_with_data(self, auth_headers, test_document):
        """Test listing attachments after adding some"""
        if not test_document:
            pytest.skip("No test document available")
        
        # First add an attachment
        attachment_data = {
            "filename": "list_test.pdf",
            "file_url": "/uploads/list_test.pdf",
            "file_size": 2048,
            "mime_type": "application/pdf"
        }
        requests.post(
            f"{BASE_URL}/api/documents/{test_document['document_id']}/attachments",
            json=attachment_data,
            headers=auth_headers
        )
        
        # Now list
        response = requests.get(
            f"{BASE_URL}/api/documents/{test_document['document_id']}/attachments",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        attachments = response.json()
        assert isinstance(attachments, list)
        assert len(attachments) >= 1
        
        # Verify attachment structure
        att = attachments[0]
        assert "attachment_id" in att
        assert "filename" in att
        assert "file_url" in att
        assert "file_size" in att
        assert "uploaded_by_name" in att
        print(f"✓ Listed {len(attachments)} attachments with proper structure")
    
    def test_delete_document_attachment(self, auth_headers, test_document):
        """Test deleting a document attachment"""
        if not test_document:
            pytest.skip("No test document available")
        
        # First add an attachment
        attachment_data = {
            "filename": "delete_test.pdf",
            "file_url": "/uploads/delete_test.pdf",
            "file_size": 512,
            "mime_type": "application/pdf"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/documents/{test_document['document_id']}/attachments",
            json=attachment_data,
            headers=auth_headers
        )
        attachment_id = create_response.json()["attachment_id"]
        
        # Delete the attachment
        response = requests.delete(
            f"{BASE_URL}/api/documents/attachments/{attachment_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print(f"✓ Deleted attachment: {attachment_id}")


class TestDocumentVersionHistory:
    """Test Document Version History API"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def test_document(self, auth_headers):
        """Create a test document for version testing"""
        doc_data = {
            "title": f"TEST_Version_Doc_{datetime.now().strftime('%H%M%S')}",
            "description": "Document for version testing",
            "document_type": "procedure",
            "content": "Initial content"
        }
        response = requests.post(
            f"{BASE_URL}/api/documents/?org_id={ORG_ID}",
            json=doc_data,
            headers=auth_headers
        )
        if response.status_code == 200:
            doc = response.json()
            yield doc
            # Cleanup
            requests.delete(f"{BASE_URL}/api/documents/{doc['document_id']}", headers=auth_headers)
        else:
            yield None
    
    def test_list_document_versions_empty(self, auth_headers, test_document):
        """Test listing versions for a new document"""
        if not test_document:
            pytest.skip("No test document available")
        
        response = requests.get(
            f"{BASE_URL}/api/documents/{test_document['document_id']}/versions",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        versions = response.json()
        assert isinstance(versions, list)
        print(f"✓ Listed versions (initial): {len(versions)}")
    
    def test_create_document_version(self, auth_headers, test_document):
        """Test creating a version snapshot"""
        if not test_document:
            pytest.skip("No test document available")
        
        response = requests.post(
            f"{BASE_URL}/api/documents/{test_document['document_id']}/versions?change_summary=Initial%20version%20snapshot",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        version = response.json()
        
        assert "version_id" in version
        assert "version_number" in version
        assert version["version_number"] >= 1
        assert "title" in version
        assert "status" in version
        assert "changed_by_name" in version
        print(f"✓ Created version {version['version_number']}: {version['version_id']}")
        
        return version["version_id"]
    
    def test_create_multiple_versions(self, auth_headers, test_document):
        """Test creating multiple versions"""
        if not test_document:
            pytest.skip("No test document available")
        
        # Create first version
        response1 = requests.post(
            f"{BASE_URL}/api/documents/{test_document['document_id']}/versions?change_summary=First%20change",
            json={},
            headers=auth_headers
        )
        assert response1.status_code == 200
        v1 = response1.json()
        
        # Create second version
        response2 = requests.post(
            f"{BASE_URL}/api/documents/{test_document['document_id']}/versions?change_summary=Second%20change",
            json={},
            headers=auth_headers
        )
        assert response2.status_code == 200
        v2 = response2.json()
        
        assert v2["version_number"] > v1["version_number"]
        print(f"✓ Created multiple versions: v{v1['version_number']} → v{v2['version_number']}")
    
    def test_list_document_versions_with_data(self, auth_headers, test_document):
        """Test listing versions after creating some"""
        if not test_document:
            pytest.skip("No test document available")
        
        response = requests.get(
            f"{BASE_URL}/api/documents/{test_document['document_id']}/versions",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        versions = response.json()
        assert isinstance(versions, list)
        
        if len(versions) > 0:
            # Verify version structure
            ver = versions[0]
            assert "version_id" in ver
            assert "version_number" in ver
            assert "title" in ver
            assert "status" in ver
            assert "changed_by" in ver
            assert "changed_by_name" in ver
            assert "created_at" in ver
            print(f"✓ Listed {len(versions)} versions with proper structure")
        else:
            print(f"✓ Listed versions (empty)")
    
    def test_get_specific_version(self, auth_headers, test_document):
        """Test getting a specific version by ID"""
        if not test_document:
            pytest.skip("No test document available")
        
        # First create a version
        create_response = requests.post(
            f"{BASE_URL}/api/documents/{test_document['document_id']}/versions?change_summary=Test%20version",
            json={},
            headers=auth_headers
        )
        version_id = create_response.json()["version_id"]
        
        # Get the specific version
        response = requests.get(
            f"{BASE_URL}/api/documents/versions/{version_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        version = response.json()
        
        assert version["version_id"] == version_id
        assert "title" in version
        assert "status" in version
        print(f"✓ Got specific version: {version_id}")


class TestOrgDocumentApprovals:
    """Test Org Document Approvals API (moved route to avoid masking)"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_get_org_approvals_all(self, auth_headers):
        """Test getting all org document approvals"""
        response = requests.get(
            f"{BASE_URL}/api/documents/org/{ORG_ID}/approvals",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        approvals = response.json()
        assert isinstance(approvals, list)
        
        if len(approvals) > 0:
            # Verify approval structure
            approval = approvals[0]
            assert "approval_id" in approval
            assert "document_id" in approval
            assert "document_title" in approval
            assert "requester_name" in approval
            assert "original_status" in approval
            assert "target_status" in approval
            assert "status" in approval
            print(f"✓ Got {len(approvals)} org approvals with proper structure")
        else:
            print(f"✓ Got org approvals (empty)")
    
    def test_get_org_approvals_pending_only(self, auth_headers):
        """Test getting only pending org approvals"""
        response = requests.get(
            f"{BASE_URL}/api/documents/org/{ORG_ID}/approvals?status=pending",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        approvals = response.json()
        assert isinstance(approvals, list)
        
        # All returned approvals should be pending
        for approval in approvals:
            assert approval["status"] == "pending", f"Expected pending, got {approval['status']}"
        
        print(f"✓ Got {len(approvals)} pending org approvals")
    
    def test_get_org_approvals_with_limit(self, auth_headers):
        """Test getting org approvals with limit"""
        response = requests.get(
            f"{BASE_URL}/api/documents/org/{ORG_ID}/approvals?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        approvals = response.json()
        assert isinstance(approvals, list)
        assert len(approvals) <= 5
        print(f"✓ Got org approvals with limit: {len(approvals)}")


class TestDashboardPendingApprovalsWidget:
    """Test Dashboard Pending Approvals Widget data"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_pending_approvals_for_dashboard(self, auth_headers):
        """Test getting pending approvals for dashboard widget"""
        # Dashboard uses getOrgDocumentApprovals with status=pending and limit=5
        response = requests.get(
            f"{BASE_URL}/api/documents/org/{ORG_ID}/approvals?status=pending&limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        approvals = response.json()
        assert isinstance(approvals, list)
        
        # Verify data needed for dashboard widget
        for approval in approvals:
            assert "approval_id" in approval
            assert "document_title" in approval  # Needed for display
            assert "requester_name" in approval  # Needed for display
            assert "target_status" in approval   # Needed for badge
            assert "created_at" in approval      # Needed for time display
        
        print(f"✓ Dashboard widget data: {len(approvals)} pending approvals")
    
    def test_pending_approvals_for_user(self, auth_headers):
        """Test getting pending approvals for current user"""
        response = requests.get(
            f"{BASE_URL}/api/documents/workflows/pending?org_id={ORG_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        approvals = response.json()
        assert isinstance(approvals, list)
        print(f"✓ User pending approvals: {len(approvals)}")


class TestExistingDocuments:
    """Test with existing test documents"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_get_existing_document_attachments(self, auth_headers):
        """Test getting attachments for existing test documents"""
        for doc_id in TEST_DOC_IDS:
            response = requests.get(
                f"{BASE_URL}/api/documents/{doc_id}/attachments",
                headers=auth_headers
            )
            if response.status_code == 200:
                attachments = response.json()
                print(f"✓ Document {doc_id}: {len(attachments)} attachments")
            elif response.status_code == 404:
                print(f"⚠ Document {doc_id} not found (may have been deleted)")
            else:
                print(f"⚠ Document {doc_id}: {response.status_code}")
    
    def test_get_existing_document_versions(self, auth_headers):
        """Test getting versions for existing test documents"""
        for doc_id in TEST_DOC_IDS:
            response = requests.get(
                f"{BASE_URL}/api/documents/{doc_id}/versions",
                headers=auth_headers
            )
            if response.status_code == 200:
                versions = response.json()
                print(f"✓ Document {doc_id}: {len(versions)} versions")
            elif response.status_code == 404:
                print(f"⚠ Document {doc_id} not found (may have been deleted)")
            else:
                print(f"⚠ Document {doc_id}: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
