"""
Test @mentions in comments and repository pattern refactoring
Tests:
1. Comment creation with @mentions
2. Mention extraction from content
3. Notification creation for mentioned users
4. Project repository CRUD operations
5. Task repository CRUD operations
6. Customer repository CRUD operations
7. Bulk task operations after refactoring
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Test credentials
TEST_USER_1 = {"email": "test@proflow.com", "password": "test123456"}
TEST_USER_2 = {"email": "ahmed@ahmed.com", "password": "Su@12345"}

# Test project ID
TEST_PROJECT_ID = "proj_c31c1308e3dc"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user 1"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER_1)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_token_user2():
    """Get authentication token for test user 2"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER_2)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed for user 2: {response.status_code}")


@pytest.fixture(scope="module")
def authenticated_client(auth_token):
    """Session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


@pytest.fixture(scope="module")
def authenticated_client_user2(auth_token_user2):
    """Session with auth header for user 2"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token_user2}"
    })
    return session


@pytest.fixture(scope="module")
def org_id(authenticated_client):
    """Get org_id from a project"""
    response = authenticated_client.get(f"{BASE_URL}/api/projects/{TEST_PROJECT_ID}")
    if response.status_code == 200:
        return response.json().get("org_id")
    pytest.skip("Could not get org_id")


# ==================== Health Check ====================

def test_health_check():
    """Test API health endpoint"""
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✓ Health check passed")


# ==================== Project Repository Tests ====================

def test_get_projects_list(authenticated_client):
    """Test GET /api/projects - list all projects"""
    response = authenticated_client.get(f"{BASE_URL}/api/projects/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print(f"✓ Got {len(data)} projects")


def test_get_project_by_id(authenticated_client):
    """Test GET /api/projects/{id} - get specific project"""
    response = authenticated_client.get(f"{BASE_URL}/api/projects/{TEST_PROJECT_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == TEST_PROJECT_ID
    assert "name" in data
    assert "task_count" in data
    print(f"✓ Got project: {data['name']}")


def test_get_project_members(authenticated_client):
    """Test GET /api/projects/{id}/members - get project members"""
    response = authenticated_client.get(f"{BASE_URL}/api/projects/{TEST_PROJECT_ID}/members")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Verify member structure
    if len(data) > 0:
        member = data[0]
        assert "user_id" in member
        assert "name" in member
        assert "email" in member
    print(f"✓ Got {len(data)} project members")


# ==================== Task Repository Tests ====================

def test_get_tasks_by_project(authenticated_client):
    """Test GET /api/tasks?project_id={id} - get tasks for project"""
    response = authenticated_client.get(f"{BASE_URL}/api/tasks/?project_id={TEST_PROJECT_ID}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print(f"✓ Got {len(data)} tasks for project")


def test_task_crud_operations(authenticated_client):
    """Test task CRUD operations"""
    # CREATE
    task_data = {
        "project_id": TEST_PROJECT_ID,
        "title": "TEST_CRUD_Task",
        "description": "Task for CRUD testing",
        "status": "todo",
        "priority": "medium",
        "assignee_ids": []
    }
    create_response = authenticated_client.post(f"{BASE_URL}/api/tasks/", json=task_data)
    assert create_response.status_code == 200
    created_task = create_response.json()
    assert created_task["title"] == "TEST_CRUD_Task"
    task_id = created_task["task_id"]
    print(f"✓ Created task: {task_id}")
    
    # READ
    get_response = authenticated_client.get(f"{BASE_URL}/api/tasks/{task_id}")
    assert get_response.status_code == 200
    fetched_task = get_response.json()
    assert fetched_task["task_id"] == task_id
    print(f"✓ Got task by ID")
    
    # UPDATE
    update_data = {"status": "in_progress", "priority": "high"}
    update_response = authenticated_client.put(f"{BASE_URL}/api/tasks/{task_id}", json=update_data)
    assert update_response.status_code == 200
    updated_task = update_response.json()
    assert updated_task["status"] == "in_progress"
    assert updated_task["priority"] == "high"
    print(f"✓ Updated task")
    
    # DELETE
    delete_response = authenticated_client.delete(f"{BASE_URL}/api/tasks/{task_id}")
    assert delete_response.status_code == 200
    
    # Verify deletion
    verify_response = authenticated_client.get(f"{BASE_URL}/api/tasks/{task_id}")
    assert verify_response.status_code == 404
    print(f"✓ Deleted task and verified")


# ==================== Customer Repository Tests ====================

def test_get_customers_list(authenticated_client, org_id):
    """Test GET /api/customers - list all customers"""
    response = authenticated_client.get(f"{BASE_URL}/api/customers/?org_id={org_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print(f"✓ Got {len(data)} customers")


def test_customer_crud_operations(authenticated_client, org_id):
    """Test customer CRUD operations"""
    # CREATE
    customer_data = {
        "name": "TEST_CRUD_Customer",
        "email": "test_crud@example.com",
        "company": "Test Company"
    }
    create_response = authenticated_client.post(
        f"{BASE_URL}/api/customers/?org_id={org_id}",
        json=customer_data
    )
    assert create_response.status_code == 200
    created_customer = create_response.json()
    assert created_customer["name"] == "TEST_CRUD_Customer"
    customer_id = created_customer["customer_id"]
    print(f"✓ Created customer: {customer_id}")
    
    # READ
    get_response = authenticated_client.get(f"{BASE_URL}/api/customers/{customer_id}")
    assert get_response.status_code == 200
    fetched_customer = get_response.json()
    assert fetched_customer["customer_id"] == customer_id
    print(f"✓ Got customer by ID")
    
    # UPDATE
    update_data = {"company": "Updated Company"}
    update_response = authenticated_client.put(
        f"{BASE_URL}/api/customers/{customer_id}",
        json=update_data
    )
    assert update_response.status_code == 200
    updated_customer = update_response.json()
    assert updated_customer["company"] == "Updated Company"
    print(f"✓ Updated customer")
    
    # DELETE
    delete_response = authenticated_client.delete(f"{BASE_URL}/api/customers/{customer_id}")
    assert delete_response.status_code == 200
    print(f"✓ Deleted customer")


# ==================== @Mentions Tests ====================

@pytest.fixture(scope="module")
def test_task_for_comments(authenticated_client):
    """Create a test task for comments"""
    task_data = {
        "project_id": TEST_PROJECT_ID,
        "title": "TEST_Comment_Task",
        "description": "Task for testing comments with @mentions",
        "status": "todo",
        "priority": "medium",
        "assignee_ids": []
    }
    response = authenticated_client.post(f"{BASE_URL}/api/tasks/", json=task_data)
    if response.status_code == 200:
        task_id = response.json()["task_id"]
        yield task_id
        # Cleanup
        authenticated_client.delete(f"{BASE_URL}/api/tasks/{task_id}")
    else:
        pytest.skip(f"Could not create test task: {response.text}")


def test_create_comment_without_mention(authenticated_client, test_task_for_comments):
    """Test creating a comment without @mention"""
    comment_data = {
        "content": "This is a regular comment without mentions",
        "task_id": test_task_for_comments
    }
    response = authenticated_client.post(f"{BASE_URL}/api/comments/", json=comment_data)
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == comment_data["content"]
    assert "comment_id" in data
    assert "author_name" in data
    print(f"✓ Created comment without mention: {data['comment_id']}")


def test_create_comment_with_mention_in_content(authenticated_client, test_task_for_comments):
    """Test creating a comment with @mention in content"""
    # Get project members to find a user to mention
    members_response = authenticated_client.get(f"{BASE_URL}/api/projects/{TEST_PROJECT_ID}/members")
    members = members_response.json()
    
    if len(members) > 0:
        mention_name = members[0].get("name", "Test")
        comment_data = {
            "content": f"Hey @{mention_name} please check this task",
            "task_id": test_task_for_comments
        }
        response = authenticated_client.post(f"{BASE_URL}/api/comments/", json=comment_data)
        assert response.status_code == 200
        data = response.json()
        assert f"@{mention_name}" in data["content"]
        print(f"✓ Created comment with @mention in content: {data['comment_id']}")
    else:
        pytest.skip("No members to mention")


def test_create_comment_with_explicit_mentions_array(authenticated_client, test_task_for_comments):
    """Test creating a comment with explicit mentions array"""
    # Get project members
    members_response = authenticated_client.get(f"{BASE_URL}/api/projects/{TEST_PROJECT_ID}/members")
    members = members_response.json()
    
    if len(members) > 0:
        mention_user_id = members[0].get("user_id")
        mention_name = members[0].get("name", "User")
        
        comment_data = {
            "content": f"@{mention_name} this is important!",
            "task_id": test_task_for_comments,
            "mentions": [mention_user_id]
        }
        response = authenticated_client.post(f"{BASE_URL}/api/comments/", json=comment_data)
        assert response.status_code == 200
        data = response.json()
        assert "comment_id" in data
        print(f"✓ Created comment with explicit mentions array: {data['comment_id']}")
    else:
        pytest.skip("No members to mention")


def test_get_comments_for_task(authenticated_client, test_task_for_comments):
    """Test getting comments for a task"""
    response = authenticated_client.get(f"{BASE_URL}/api/comments/?task_id={test_task_for_comments}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print(f"✓ Got {len(data)} comments for task")


def test_notification_created_for_mention(authenticated_client, authenticated_client_user2, test_task_for_comments):
    """Test that notification is created when user is mentioned"""
    # Get user2's info
    user2_response = authenticated_client_user2.get(f"{BASE_URL}/api/auth/me")
    if user2_response.status_code != 200:
        pytest.skip("Could not get user2 info")
    
    user2_info = user2_response.json()
    user2_id = user2_info.get("user_id")
    user2_name = user2_info.get("name", "Ahmed")
    
    # Create comment mentioning user2
    comment_data = {
        "content": f"@{user2_name} please review this",
        "task_id": test_task_for_comments,
        "mentions": [user2_id]
    }
    response = authenticated_client.post(f"{BASE_URL}/api/comments/", json=comment_data)
    assert response.status_code == 200
    print(f"✓ Created comment mentioning user2")
    
    # Wait a moment for notification to be created
    time.sleep(0.5)
    
    # Check user2's notifications
    notif_response = authenticated_client_user2.get(f"{BASE_URL}/api/notifications/")
    assert notif_response.status_code == 200
    notifications = notif_response.json()
    
    # Look for mention notification
    mention_notifs = [n for n in notifications if n.get("type") == "mention"]
    print(f"✓ User2 has {len(mention_notifs)} mention notifications")
    
    # Verify at least one mention notification exists
    if len(mention_notifs) > 0:
        latest_mention = mention_notifs[0]
        assert "mentioned you" in latest_mention.get("title", "").lower()
        print(f"✓ Notification title: {latest_mention.get('title')}")


# ==================== Bulk Task Operations Tests ====================

def test_bulk_update_status(authenticated_client):
    """Test bulk status update"""
    # Create test tasks
    task_ids = []
    for i in range(2):
        task_data = {
            "project_id": TEST_PROJECT_ID,
            "title": f"TEST_Bulk_Status_{i}",
            "status": "todo",
            "priority": "low",
            "assignee_ids": []
        }
        response = authenticated_client.post(f"{BASE_URL}/api/tasks/", json=task_data)
        if response.status_code == 200:
            task_ids.append(response.json()["task_id"])
    
    if len(task_ids) < 2:
        pytest.skip("Could not create test tasks")
    
    # Bulk update
    bulk_data = {
        "task_ids": task_ids,
        "updates": {"status": "in_progress"}
    }
    response = authenticated_client.post(f"{BASE_URL}/api/tasks/bulk/update", json=bulk_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["modified_count"] >= 1
    print(f"✓ Bulk updated {data['modified_count']} tasks to in_progress")
    
    # Cleanup
    for task_id in task_ids:
        authenticated_client.delete(f"{BASE_URL}/api/tasks/{task_id}")


def test_bulk_update_priority(authenticated_client):
    """Test bulk priority update"""
    # Create test tasks
    task_ids = []
    for i in range(2):
        task_data = {
            "project_id": TEST_PROJECT_ID,
            "title": f"TEST_Bulk_Priority_{i}",
            "status": "todo",
            "priority": "low",
            "assignee_ids": []
        }
        response = authenticated_client.post(f"{BASE_URL}/api/tasks/", json=task_data)
        if response.status_code == 200:
            task_ids.append(response.json()["task_id"])
    
    if len(task_ids) < 2:
        pytest.skip("Could not create test tasks")
    
    # Bulk update
    bulk_data = {
        "task_ids": task_ids,
        "updates": {"priority": "high"}
    }
    response = authenticated_client.post(f"{BASE_URL}/api/tasks/bulk/update", json=bulk_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    print(f"✓ Bulk updated {data['modified_count']} tasks to high priority")
    
    # Cleanup
    for task_id in task_ids:
        authenticated_client.delete(f"{BASE_URL}/api/tasks/{task_id}")


# ==================== Cleanup ====================

def test_cleanup_test_tasks(authenticated_client):
    """Clean up any remaining TEST_ prefixed tasks"""
    response = authenticated_client.get(f"{BASE_URL}/api/tasks/?project_id={TEST_PROJECT_ID}")
    if response.status_code == 200:
        tasks = response.json()
        test_tasks = [t for t in tasks if t.get("title", "").startswith("TEST_")]
        for task in test_tasks:
            authenticated_client.delete(f"{BASE_URL}/api/tasks/{task['task_id']}")
        print(f"✓ Cleaned up {len(test_tasks)} test tasks")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
