"""
Test file for bug fixes:
1. Checklist items saving (subtasks field)
2. File upload error handling (_id field removal)
3. @mentions feature (new MentionInput component)
"""
import pytest
import requests
import os
import tempfile

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

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
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_login_success(self):
        """Test login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        print(f"✓ Login successful for {TEST_EMAIL}")


class TestChecklistBugFix:
    """Bug Fix 1: Checklist items should save when adding or marking complete"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def test_task(self, auth_headers):
        """Get or create a test task"""
        # First get projects
        response = requests.get(f"{BASE_URL}/api/projects/", headers=auth_headers)
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) > 0, "No projects found"
        
        project_id = projects[0]["project_id"]
        
        # Get tasks for this project
        response = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=auth_headers)
        assert response.status_code == 200
        tasks = response.json()
        
        if tasks:
            return tasks[0]
        
        # Create a test task if none exist
        response = requests.post(f"{BASE_URL}/api/tasks/", headers=auth_headers, json={
            "project_id": project_id,
            "title": "TEST_ChecklistTask",
            "description": "Task for testing checklist",
            "status": "todo",
            "priority": "medium"
        })
        assert response.status_code == 200
        return response.json()
    
    def test_add_checklist_item(self, auth_headers, test_task):
        """Test adding a checklist item saves to subtasks field"""
        task_id = test_task["task_id"]
        
        # Add a checklist item
        response = requests.post(
            f"{BASE_URL}/api/tasks/{task_id}/checklist",
            headers=auth_headers,
            json={"title": "TEST_ChecklistItem_1", "completed": False}
        )
        assert response.status_code == 200, f"Failed to add checklist item: {response.text}"
        
        item = response.json()
        assert "item_id" in item, "No item_id in response"
        assert item["title"] == "TEST_ChecklistItem_1"
        assert item["completed"] == False
        print(f"✓ Checklist item added: {item['item_id']}")
        
        # Verify it's saved in the task's subtasks field
        response = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        task = response.json()
        
        # Check subtasks field exists and contains our item
        subtasks = task.get("subtasks", [])
        assert len(subtasks) > 0, "Subtasks field is empty after adding checklist item"
        
        found = any(s.get("title") == "TEST_ChecklistItem_1" for s in subtasks)
        assert found, "Checklist item not found in subtasks field"
        print(f"✓ Checklist item persisted in subtasks field")
        
        return item
    
    def test_toggle_checklist_item(self, auth_headers, test_task):
        """Test marking checklist item as complete saves correctly"""
        task_id = test_task["task_id"]
        
        # First add a new item
        response = requests.post(
            f"{BASE_URL}/api/tasks/{task_id}/checklist",
            headers=auth_headers,
            json={"title": "TEST_ToggleItem", "completed": False}
        )
        assert response.status_code == 200
        item = response.json()
        item_id = item["item_id"]
        
        # Toggle to completed
        response = requests.put(
            f"{BASE_URL}/api/tasks/{task_id}/checklist/{item_id}",
            headers=auth_headers,
            json={"completed": True}
        )
        assert response.status_code == 200, f"Failed to toggle checklist item: {response.text}"
        print(f"✓ Checklist item toggled to completed")
        
        # Verify the change persisted
        response = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        task = response.json()
        
        subtasks = task.get("subtasks", [])
        item_found = next((s for s in subtasks if s.get("item_id") == item_id), None)
        assert item_found is not None, "Item not found in subtasks"
        assert item_found.get("completed") == True, "Item completed status not saved"
        print(f"✓ Checklist item completed status persisted")
    
    def test_delete_checklist_item(self, auth_headers, test_task):
        """Test deleting checklist item"""
        task_id = test_task["task_id"]
        
        # Add an item to delete
        response = requests.post(
            f"{BASE_URL}/api/tasks/{task_id}/checklist",
            headers=auth_headers,
            json={"title": "TEST_DeleteItem", "completed": False}
        )
        assert response.status_code == 200
        item = response.json()
        item_id = item["item_id"]
        
        # Delete the item
        response = requests.delete(
            f"{BASE_URL}/api/tasks/{task_id}/checklist/{item_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to delete checklist item: {response.text}"
        print(f"✓ Checklist item deleted")
        
        # Verify deletion
        response = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        task = response.json()
        
        subtasks = task.get("subtasks", [])
        item_found = any(s.get("item_id") == item_id for s in subtasks)
        assert not item_found, "Deleted item still exists in subtasks"
        print(f"✓ Checklist item deletion persisted")


class TestFileUploadBugFix:
    """Bug Fix 2: File upload should not show error when upload succeeds"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def test_task(self, auth_headers):
        """Get or create a test task"""
        response = requests.get(f"{BASE_URL}/api/projects/", headers=auth_headers)
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) > 0
        
        project_id = projects[0]["project_id"]
        response = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=auth_headers)
        assert response.status_code == 200
        tasks = response.json()
        
        if tasks:
            return tasks[0]
        
        response = requests.post(f"{BASE_URL}/api/tasks/", headers=auth_headers, json={
            "project_id": project_id,
            "title": "TEST_FileUploadTask",
            "status": "todo",
            "priority": "medium"
        })
        assert response.status_code == 200
        return response.json()
    
    def test_upload_file_returns_valid_json(self, auth_token, test_task):
        """Test file upload returns valid JSON without _id field"""
        task_id = test_task["task_id"]
        
        # Create a test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test file content for upload")
            temp_path = f.name
        
        try:
            # Upload the file
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/tasks/{task_id}/attachments",
                    headers={"Authorization": f"Bearer {auth_token}"},
                    files={"file": ("test_upload.txt", f, "text/plain")}
                )
            
            assert response.status_code == 200, f"Upload failed: {response.text}"
            
            # Verify response is valid JSON
            attachment = response.json()
            assert "attachment_id" in attachment, "No attachment_id in response"
            assert "filename" in attachment, "No filename in response"
            
            # CRITICAL: Verify _id is NOT in response (this was the bug)
            assert "_id" not in attachment, "_id field should not be in response (causes JSON serialization error)"
            
            print(f"✓ File uploaded successfully: {attachment['attachment_id']}")
            print(f"✓ Response does not contain _id field (bug fix verified)")
            
            return attachment
            
        finally:
            os.unlink(temp_path)
    
    def test_get_attachments_no_id_field(self, auth_headers, test_task):
        """Test getting attachments doesn't include _id field"""
        task_id = test_task["task_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/tasks/{task_id}/attachments",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        attachments = response.json()
        for att in attachments:
            assert "_id" not in att, f"_id field found in attachment: {att}"
        
        print(f"✓ GET attachments returns {len(attachments)} items without _id field")
    
    def test_delete_attachment(self, auth_token, auth_headers, test_task):
        """Test deleting an attachment"""
        task_id = test_task["task_id"]
        
        # First upload a file to delete
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("File to delete")
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/tasks/{task_id}/attachments",
                    headers={"Authorization": f"Bearer {auth_token}"},
                    files={"file": ("delete_me.txt", f, "text/plain")}
                )
            assert response.status_code == 200
            attachment = response.json()
            attachment_id = attachment["attachment_id"]
            
            # Delete the attachment
            response = requests.delete(
                f"{BASE_URL}/api/tasks/{task_id}/attachments/{attachment_id}",
                headers=auth_headers
            )
            assert response.status_code == 200
            print(f"✓ Attachment deleted: {attachment_id}")
            
        finally:
            os.unlink(temp_path)


class TestMentionsFeature:
    """New Feature: @mentions UI with autocomplete"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def test_task(self, auth_headers):
        """Get a test task"""
        response = requests.get(f"{BASE_URL}/api/projects/", headers=auth_headers)
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) > 0
        
        project_id = projects[0]["project_id"]
        response = requests.get(f"{BASE_URL}/api/tasks/?project_id={project_id}", headers=auth_headers)
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) > 0
        return tasks[0]
    
    def test_get_project_members_for_mentions(self, auth_headers, test_task):
        """Test getting project members (needed for @mention autocomplete)"""
        project_id = test_task["project_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/projects/{project_id}/members",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        members = response.json()
        assert isinstance(members, list), "Members should be a list"
        
        # Verify member structure has fields needed for mentions
        if members:
            member = members[0]
            assert "user_id" in member, "Member should have user_id"
            assert "name" in member, "Member should have name"
            # email is optional but useful for mentions
            print(f"✓ Got {len(members)} project members for @mention autocomplete")
            for m in members[:3]:  # Show first 3
                print(f"  - {m.get('name', 'Unknown')} ({m.get('email', 'no email')})")
        else:
            print("⚠ No members found in project")
    
    def test_create_comment_with_mention(self, auth_headers, test_task):
        """Test creating a comment with @mention"""
        task_id = test_task["task_id"]
        
        # Create a comment with @mention syntax
        response = requests.post(
            f"{BASE_URL}/api/comments/",
            headers=auth_headers,
            json={
                "task_id": task_id,
                "content": "Hey @Test User, please review this task!"
            }
        )
        assert response.status_code == 200, f"Failed to create comment: {response.text}"
        
        comment = response.json()
        assert "comment_id" in comment
        assert "@Test User" in comment.get("content", "")
        print(f"✓ Comment with @mention created: {comment['comment_id']}")
    
    def test_get_comments_with_mentions(self, auth_headers, test_task):
        """Test getting comments preserves @mention text"""
        task_id = test_task["task_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/comments/?task_id={task_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        comments = response.json()
        print(f"✓ Got {len(comments)} comments for task")
        
        # Check if any comments have @mentions
        mentions_found = [c for c in comments if "@" in c.get("content", "")]
        if mentions_found:
            print(f"✓ Found {len(mentions_found)} comments with @mentions")


class TestSpecificTask:
    """Test the specific task mentioned in the bug report: task_a470f2ac068e"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_specific_task(self, auth_headers):
        """Test getting the specific task mentioned in bug report"""
        task_id = "task_a470f2ac068e"
        
        response = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)
        
        if response.status_code == 404:
            print(f"⚠ Task {task_id} not found - may have been deleted")
            pytest.skip("Specific task not found")
        
        assert response.status_code == 200, f"Failed to get task: {response.text}"
        
        task = response.json()
        print(f"✓ Task found: {task.get('title', 'Unknown')}")
        
        # Check subtasks/checklist
        subtasks = task.get("subtasks", [])
        print(f"  - Subtasks/Checklist items: {len(subtasks)}")
        for s in subtasks[:5]:
            status = "✓" if s.get("completed") else "○"
            print(f"    {status} {s.get('title', 'Unknown')}")
        
        # Check attachments
        response = requests.get(f"{BASE_URL}/api/tasks/{task_id}/attachments", headers=auth_headers)
        if response.status_code == 200:
            attachments = response.json()
            print(f"  - Attachments: {len(attachments)}")
            for a in attachments[:3]:
                print(f"    📎 {a.get('original_filename', a.get('filename', 'Unknown'))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
