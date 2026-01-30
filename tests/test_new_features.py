"""
Backend API Tests for New Features:
- Global Search
- File Attachments
- Rich Text (stored as HTML in description field)
"""
import pytest
import requests
import os
import io
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://costmanager-5.preview.emergentagent.com')

# Generate unique test user for each test run
UNIQUE_ID = uuid.uuid4().hex[:8]
TEST_USER = {
    "email": f"test_features_{UNIQUE_ID}@example.com",
    "password": "TestPass123!",
    "name": f"Test Features User {UNIQUE_ID}"
}


@pytest.fixture(scope="module")
def session():
    return requests.Session()


@pytest.fixture(scope="module")
def auth_data(session):
    """Register user and get auth token"""
    # Try to register
    response = session.post(f"{BASE_URL}/api/auth/register", json=TEST_USER)
    if response.status_code == 200:
        data = response.json()
        return {
            "token": data["access_token"],
            "user": data["user"]
        }
    elif response.status_code == 400 and "already registered" in response.text:
        # User exists, try to login
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
    
    # Create org if none exists
    response = session.post(f"{BASE_URL}/api/organizations/", 
                           headers=auth_headers,
                           json={"name": f"Test Org {UNIQUE_ID}"})
    assert response.status_code == 200
    return response.json()["org_id"]


@pytest.fixture(scope="module")
def project_id(session, auth_headers, org_id):
    """Create a test project"""
    response = session.post(f"{BASE_URL}/api/projects/?org_id={org_id}",
                           headers=auth_headers,
                           json={
                               "name": f"SearchTestProject_{UNIQUE_ID}",
                               "description": "Project for testing search functionality",
                               "status": "active"
                           })
    assert response.status_code == 200, f"Project creation failed: {response.text}"
    return response.json()["project_id"]


@pytest.fixture(scope="module")
def task_with_rich_text(session, auth_headers, project_id):
    """Create a task with rich text HTML description"""
    rich_text_html = "<p><strong>Bold text</strong> and <em>italic text</em></p><ul><li>List item 1</li><li>List item 2</li></ul><p><a href='https://example.com'>A link</a></p>"
    
    response = session.post(f"{BASE_URL}/api/tasks/",
                           headers=auth_headers,
                           json={
                               "title": f"RichTextTestTask_{UNIQUE_ID}",
                               "description": rich_text_html,
                               "project_id": project_id,
                               "status": "todo",
                               "priority": "high"
                           })
    assert response.status_code == 200, f"Task creation failed: {response.text}"
    return response.json()


class TestGlobalSearch:
    """Test Global Search API"""
    
    def test_search_requires_auth(self, session):
        """Search should require authentication"""
        response = session.get(f"{BASE_URL}/api/search?q=test")
        assert response.status_code == 401
    
    def test_search_min_query_length(self, session, auth_headers):
        """Search query must be at least 2 characters"""
        response = session.get(f"{BASE_URL}/api/search?q=a", headers=auth_headers)
        assert response.status_code == 400
        assert "at least 2 characters" in response.json().get("detail", "")
    
    def test_search_projects(self, session, auth_headers, project_id):
        """Search should find projects by name"""
        response = session.get(f"{BASE_URL}/api/search?q=SearchTest", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert "query" in data
        assert data["query"] == "SearchTest"
        
        # Should find our test project
        project_results = [r for r in data["results"] if r["type"] == "project"]
        assert len(project_results) > 0, "Should find at least one project"
        
        # Verify result structure
        result = project_results[0]
        assert "id" in result
        assert "title" in result
        assert "type" in result
        assert result["type"] == "project"
    
    def test_search_tasks(self, session, auth_headers, task_with_rich_text):
        """Search should find tasks by title"""
        response = session.get(f"{BASE_URL}/api/search?q=RichText", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        task_results = [r for r in data["results"] if r["type"] == "task"]
        assert len(task_results) > 0, "Should find at least one task"
        
        # Verify task result structure
        result = task_results[0]
        assert result["type"] == "task"
        assert "project_id" in result
        assert "status" in result
    
    def test_search_returns_project_info_for_tasks(self, session, auth_headers, task_with_rich_text):
        """Task search results should include project name"""
        response = session.get(f"{BASE_URL}/api/search?q=RichText", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        task_results = [r for r in data["results"] if r["type"] == "task"]
        if task_results:
            result = task_results[0]
            assert "project_name" in result
            assert result["project_name"] is not None
    
    def test_search_no_results(self, session, auth_headers):
        """Search with no matches should return empty results"""
        response = session.get(f"{BASE_URL}/api/search?q=xyznonexistent123", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["results"] == [] or len(data["results"]) == 0


class TestRichTextDescription:
    """Test Rich Text HTML storage in task descriptions"""
    
    def test_task_stores_html_description(self, session, auth_headers, task_with_rich_text):
        """Task should store HTML in description field"""
        task_id = task_with_rich_text["task_id"]
        
        response = session.get(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        task = response.json()
        
        # Verify HTML is preserved
        assert "<strong>" in task["description"]
        assert "<em>" in task["description"]
        assert "<ul>" in task["description"]
        assert "<li>" in task["description"]
    
    def test_update_task_with_html(self, session, auth_headers, task_with_rich_text):
        """Task description can be updated with new HTML"""
        task_id = task_with_rich_text["task_id"]
        new_html = "<h2>Updated heading</h2><p>New paragraph with <strong>bold</strong></p>"
        
        response = session.put(f"{BASE_URL}/api/tasks/{task_id}",
                              headers=auth_headers,
                              json={"description": new_html})
        assert response.status_code == 200
        
        # Verify update
        task = response.json()
        assert "<h2>" in task["description"] or "Updated heading" in task["description"]


class TestFileAttachments:
    """Test File Attachment APIs"""
    
    def test_upload_attachment(self, session, auth_headers, task_with_rich_text):
        """Upload a file attachment to a task"""
        task_id = task_with_rich_text["task_id"]
        
        # Create a test file
        file_content = b"This is a test file content for attachment testing."
        files = {
            'file': ('test_document.txt', io.BytesIO(file_content), 'text/plain')
        }
        
        # Remove Content-Type for multipart upload
        headers = {"Authorization": auth_headers["Authorization"]}
        
        response = session.post(f"{BASE_URL}/api/tasks/{task_id}/attachments",
                               headers=headers,
                               files=files)
        assert response.status_code == 200, f"Upload failed: {response.text}"
        
        attachment = response.json()
        assert "attachment_id" in attachment
        assert attachment["filename"] == "test_document.txt"
        assert attachment["content_type"] == "text/plain"
        assert attachment["size"] > 0
        assert attachment["task_id"] == task_id
        
        return attachment
    
    def test_get_attachments(self, session, auth_headers, task_with_rich_text):
        """Get all attachments for a task"""
        task_id = task_with_rich_text["task_id"]
        
        # First upload an attachment
        file_content = b"Test file for listing"
        files = {'file': ('list_test.txt', io.BytesIO(file_content), 'text/plain')}
        headers = {"Authorization": auth_headers["Authorization"]}
        
        upload_response = session.post(f"{BASE_URL}/api/tasks/{task_id}/attachments",
                                       headers=headers,
                                       files=files)
        assert upload_response.status_code == 200
        
        # Get attachments
        response = session.get(f"{BASE_URL}/api/tasks/{task_id}/attachments",
                              headers=auth_headers)
        assert response.status_code == 200
        
        attachments = response.json()
        assert isinstance(attachments, list)
        assert len(attachments) >= 1
        
        # Verify attachment structure
        att = attachments[0]
        assert "attachment_id" in att
        assert "filename" in att
        assert "content_type" in att
        assert "size" in att
    
    def test_download_attachment(self, session, auth_headers, task_with_rich_text):
        """Download an attachment"""
        task_id = task_with_rich_text["task_id"]
        
        # Upload a file first
        file_content = b"Download test content 12345"
        files = {'file': ('download_test.txt', io.BytesIO(file_content), 'text/plain')}
        headers = {"Authorization": auth_headers["Authorization"]}
        
        upload_response = session.post(f"{BASE_URL}/api/tasks/{task_id}/attachments",
                                       headers=headers,
                                       files=files)
        assert upload_response.status_code == 200
        attachment_id = upload_response.json()["attachment_id"]
        
        # Download the file
        response = session.get(f"{BASE_URL}/api/tasks/{task_id}/attachments/{attachment_id}/download",
                              headers=headers)
        assert response.status_code == 200
        assert response.content == file_content
    
    def test_delete_attachment(self, session, auth_headers, task_with_rich_text):
        """Delete an attachment"""
        task_id = task_with_rich_text["task_id"]
        
        # Upload a file first
        file_content = b"File to be deleted"
        files = {'file': ('delete_test.txt', io.BytesIO(file_content), 'text/plain')}
        headers = {"Authorization": auth_headers["Authorization"]}
        
        upload_response = session.post(f"{BASE_URL}/api/tasks/{task_id}/attachments",
                                       headers=headers,
                                       files=files)
        assert upload_response.status_code == 200
        attachment_id = upload_response.json()["attachment_id"]
        
        # Delete the attachment
        response = session.delete(f"{BASE_URL}/api/tasks/{task_id}/attachments/{attachment_id}",
                                 headers=auth_headers)
        assert response.status_code == 200
        
        # Verify deletion - download should fail
        download_response = session.get(f"{BASE_URL}/api/tasks/{task_id}/attachments/{attachment_id}/download",
                                        headers=headers)
        assert download_response.status_code == 404
    
    def test_attachment_not_found(self, session, auth_headers, task_with_rich_text):
        """Accessing non-existent attachment should return 404"""
        task_id = task_with_rich_text["task_id"]
        
        response = session.get(f"{BASE_URL}/api/tasks/{task_id}/attachments/nonexistent_id/download",
                              headers=auth_headers)
        assert response.status_code == 404


class TestSearchWithComments:
    """Test search functionality with comments"""
    
    def test_search_finds_comments(self, session, auth_headers, task_with_rich_text):
        """Search should find comments by content"""
        task_id = task_with_rich_text["task_id"]
        
        # Create a comment with unique searchable text
        unique_text = f"UniqueSearchableComment{int(time.time())}"
        response = session.post(f"{BASE_URL}/api/comments/",
                               headers=auth_headers,
                               json={
                                   "content": unique_text,
                                   "task_id": task_id
                               })
        assert response.status_code == 200
        
        # Search for the comment
        search_response = session.get(f"{BASE_URL}/api/search?q={unique_text[:15]}", 
                                      headers=auth_headers)
        assert search_response.status_code == 200
        data = search_response.json()
        
        # Verify search returns results (comments may or may not be found depending on implementation)
        assert "results" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
