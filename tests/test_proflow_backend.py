"""
ProFlow Backend API Tests
Tests for the refactored modular architecture with routers, services, core modules, and models.
Covers: Authentication, Dashboard, Organizations, Projects, Tasks, Search, Time Entries, Comments, Subscriptions
"""
import pytest
import requests
import os
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://approvalmate-3.preview.emergentagent.com"

# Test credentials
TEST_EMAIL = "test@proflow.com"
TEST_PASSWORD = "test123456"


class TestHealthCheck:
    """Health check endpoint tests - run first to verify API is up"""
    
    def test_health_endpoint(self):
        """Test GET /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "2.0.0"
        print(f"✓ Health check passed - version {data['version']}")


class TestAuthentication:
    """Authentication flow tests"""
    
    def test_login_success(self):
        """Test POST /api/auth/login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == TEST_EMAIL
        print(f"✓ Login successful for {TEST_EMAIL}")
        
        return data["access_token"]
    
    def test_login_invalid_credentials(self):
        """Test POST /api/auth/login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")
    
    def test_get_me_authenticated(self):
        """Test GET /api/auth/me with valid token"""
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Get current user
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Get me failed: {response.text}"
        data = response.json()
        assert data["email"] == TEST_EMAIL
        print(f"✓ Get current user successful: {data['name']}")
    
    def test_get_me_unauthenticated(self):
        """Test GET /api/auth/me without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated request correctly rejected")


class TestDashboard:
    """Dashboard API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_response.status_code == 200, "Login failed in setup"
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_dashboard(self):
        """Test GET /api/dashboard/ returns dashboard data"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        
        data = response.json()
        # Verify dashboard structure
        assert "projects" in data, "Missing projects in dashboard"
        assert "tasks" in data, "Missing tasks in dashboard"
        assert "recent_tasks" in data, "Missing recent_tasks in dashboard"
        assert "upcoming_deadlines" in data, "Missing upcoming_deadlines in dashboard"
        assert "recent_activity" in data, "Missing recent_activity in dashboard"
        
        # Verify nested structure
        assert "total" in data["projects"]
        assert "active" in data["projects"]
        assert "total" in data["tasks"]
        assert "completed" in data["tasks"]
        
        print(f"✓ Dashboard loaded - {data['projects']['total']} projects, {data['tasks']['total']} tasks")
    
    def test_get_my_tasks(self):
        """Test GET /api/dashboard/my-tasks returns user's tasks"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/my-tasks",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"My tasks failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of tasks"
        print(f"✓ My tasks loaded - {len(data)} tasks assigned to user")
    
    def test_get_quick_stats(self):
        """Test GET /api/dashboard/stats returns quick stats"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Quick stats failed: {response.text}"
        
        data = response.json()
        assert "projects" in data
        assert "tasks" in data
        assert "my_pending_tasks" in data
        assert "unread_notifications" in data
        print(f"✓ Quick stats loaded - {data['projects']} projects, {data['my_pending_tasks']} pending tasks")


class TestOrganizations:
    """Organizations API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_response.status_code == 200, "Login failed in setup"
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_organizations(self):
        """Test GET /api/organizations/ returns user's organizations"""
        response = requests.get(
            f"{BASE_URL}/api/organizations/",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get organizations failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of organizations"
        assert len(data) > 0, "User should have at least one organization"
        
        # Verify organization structure
        org = data[0]
        assert "org_id" in org
        assert "name" in org
        
        print(f"✓ Organizations loaded - {len(data)} organizations")
        return data[0]["org_id"]
    
    def test_get_organization_by_id(self):
        """Test GET /api/organizations/{org_id} returns specific organization"""
        # First get list to get an org_id
        list_response = requests.get(
            f"{BASE_URL}/api/organizations/",
            headers=self.headers
        )
        assert list_response.status_code == 200
        org_id = list_response.json()[0]["org_id"]
        
        # Get specific organization
        response = requests.get(
            f"{BASE_URL}/api/organizations/{org_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get organization failed: {response.text}"
        
        data = response.json()
        assert data["org_id"] == org_id
        print(f"✓ Organization retrieved: {data['name']}")
    
    def test_get_organization_members(self):
        """Test GET /api/organizations/{org_id}/members returns members"""
        # First get list to get an org_id
        list_response = requests.get(
            f"{BASE_URL}/api/organizations/",
            headers=self.headers
        )
        assert list_response.status_code == 200
        org_id = list_response.json()[0]["org_id"]
        
        # Get members
        response = requests.get(
            f"{BASE_URL}/api/organizations/{org_id}/members",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get members failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of members"
        assert len(data) > 0, "Organization should have at least one member"
        
        # Verify member structure
        member = data[0]
        assert "user_id" in member
        assert "email" in member
        assert "org_role" in member
        
        print(f"✓ Organization members loaded - {len(data)} members")


class TestProjects:
    """Projects API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and org_id before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_response.status_code == 200, "Login failed in setup"
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get org_id
        org_response = requests.get(
            f"{BASE_URL}/api/organizations/",
            headers=self.headers
        )
        assert org_response.status_code == 200
        self.org_id = org_response.json()[0]["org_id"]
    
    def test_get_projects(self):
        """Test GET /api/projects/ returns user's projects"""
        response = requests.get(
            f"{BASE_URL}/api/projects/",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get projects failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of projects"
        
        if len(data) > 0:
            project = data[0]
            assert "project_id" in project
            assert "name" in project
            assert "status" in project
        
        print(f"✓ Projects loaded - {len(data)} projects")
    
    def test_create_project_limit_reached(self):
        """Test POST /api/projects/ returns 403 when project limit reached"""
        project_data = {
            "name": f"TEST_Project_{datetime.now().strftime('%H%M%S')}",
            "description": "Test project created by automated tests",
            "status": "active"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/projects/?org_id={self.org_id}",
            headers=self.headers,
            json=project_data
        )
        
        # Project limit is reached for free plan, so expect 403
        assert response.status_code == 403, f"Expected 403 (limit reached), got {response.status_code}"
        assert "limit" in response.json().get("detail", "").lower()
        print("✓ Project creation correctly blocked due to plan limit")
    
    def test_get_project_by_id(self):
        """Test GET /api/projects/{project_id} returns specific project"""
        # Get existing projects
        list_response = requests.get(
            f"{BASE_URL}/api/projects/",
            headers=self.headers
        )
        assert list_response.status_code == 200
        projects = list_response.json()
        assert len(projects) > 0, "Need at least one project to test"
        
        project_id = projects[0]["project_id"]
        
        # Get specific project
        response = requests.get(
            f"{BASE_URL}/api/projects/{project_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get project failed: {response.text}"
        
        data = response.json()
        assert data["project_id"] == project_id
        print(f"✓ Project retrieved: {data['name']}")


class TestTasks:
    """Tasks API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token, org_id, and create a test project"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_response.status_code == 200, "Login failed in setup"
        self.token = login_response.json()["access_token"]
        self.user_id = login_response.json()["user"]["user_id"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get org_id
        org_response = requests.get(
            f"{BASE_URL}/api/organizations/",
            headers=self.headers
        )
        assert org_response.status_code == 200
        self.org_id = org_response.json()[0]["org_id"]
        
        # Get or create a project for tasks
        projects_response = requests.get(
            f"{BASE_URL}/api/projects/",
            headers=self.headers
        )
        assert projects_response.status_code == 200
        projects = projects_response.json()
        
        if len(projects) > 0:
            self.project_id = projects[0]["project_id"]
        else:
            # Create a project
            create_response = requests.post(
                f"{BASE_URL}/api/projects/?org_id={self.org_id}",
                headers=self.headers,
                json={"name": "TEST_TaskProject", "status": "active"}
            )
            assert create_response.status_code == 200
            self.project_id = create_response.json()["project_id"]
    
    def test_get_tasks(self):
        """Test GET /api/tasks/ returns tasks"""
        response = requests.get(
            f"{BASE_URL}/api/tasks/",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get tasks failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of tasks"
        
        print(f"✓ Tasks loaded - {len(data)} tasks")
        return data
    
    def test_get_tasks_by_project(self):
        """Test GET /api/tasks/?project_id={project_id} returns project tasks"""
        response = requests.get(
            f"{BASE_URL}/api/tasks/?project_id={self.project_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get project tasks failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of tasks"
        
        print(f"✓ Project tasks loaded - {len(data)} tasks in project")
    
    def test_create_task(self):
        """Test POST /api/tasks/ creates a new task"""
        task_data = {
            "project_id": self.project_id,
            "title": f"TEST_Task_{datetime.now().strftime('%H%M%S')}",
            "description": "Test task created by automated tests",
            "status": "todo",
            "priority": "medium",
            "assignee_ids": [self.user_id]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=self.headers,
            json=task_data
        )
        
        assert response.status_code == 200, f"Create task failed: {response.text}"
        
        data = response.json()
        assert data["title"] == task_data["title"]
        assert data["project_id"] == self.project_id
        assert "task_id" in data
        
        print(f"✓ Task created: {data['title']} (ID: {data['task_id']})")
        return data["task_id"]
    
    def test_get_task_by_id(self):
        """Test GET /api/tasks/{task_id} returns specific task"""
        # First create a task
        task_data = {
            "project_id": self.project_id,
            "title": f"TEST_GetTask_{datetime.now().strftime('%H%M%S')}",
            "status": "todo",
            "priority": "low",
            "assignee_ids": []
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=self.headers,
            json=task_data
        )
        assert create_response.status_code == 200
        task_id = create_response.json()["task_id"]
        
        # Get specific task
        response = requests.get(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get task failed: {response.text}"
        
        data = response.json()
        assert data["task_id"] == task_id
        assert data["title"] == task_data["title"]
        print(f"✓ Task retrieved: {data['title']}")


class TestSearch:
    """Search API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_response.status_code == 200, "Login failed in setup"
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_global_search(self):
        """Test GET /api/search/?q=test performs global search"""
        response = requests.get(
            f"{BASE_URL}/api/search/?q=test",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Search failed: {response.text}"
        
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "query" in data
        assert data["query"] == "test"
        assert isinstance(data["results"], list)
        
        print(f"✓ Search completed - {data['total']} results for 'test'")
    
    def test_search_by_type(self):
        """Test GET /api/search/?q=test&type=project filters by type"""
        response = requests.get(
            f"{BASE_URL}/api/search/?q=test&type=project",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Search by type failed: {response.text}"
        
        data = response.json()
        # All results should be projects
        for result in data["results"]:
            assert result["type"] == "project", f"Expected project, got {result['type']}"
        
        print(f"✓ Search by type completed - {data['total']} project results")
    
    def test_search_minimum_query_length(self):
        """Test search requires minimum 2 characters"""
        response = requests.get(
            f"{BASE_URL}/api/search/?q=a",
            headers=self.headers
        )
        
        # Should return 422 validation error for query too short
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Search correctly validates minimum query length")


class TestTimeEntries:
    """Time Entries API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and create a test task"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_response.status_code == 200, "Login failed in setup"
        self.token = login_response.json()["access_token"]
        self.user_id = login_response.json()["user"]["user_id"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get org_id
        org_response = requests.get(
            f"{BASE_URL}/api/organizations/",
            headers=self.headers
        )
        assert org_response.status_code == 200
        self.org_id = org_response.json()[0]["org_id"]
        
        # Get or create a project
        projects_response = requests.get(
            f"{BASE_URL}/api/projects/",
            headers=self.headers
        )
        assert projects_response.status_code == 200
        projects = projects_response.json()
        
        if len(projects) > 0:
            self.project_id = projects[0]["project_id"]
        else:
            create_response = requests.post(
                f"{BASE_URL}/api/projects/?org_id={self.org_id}",
                headers=self.headers,
                json={"name": "TEST_TimeProject", "status": "active"}
            )
            assert create_response.status_code == 200
            self.project_id = create_response.json()["project_id"]
        
        # Create a task for time entries
        task_response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=self.headers,
            json={
                "project_id": self.project_id,
                "title": f"TEST_TimeTask_{datetime.now().strftime('%H%M%S')}",
                "status": "todo",
                "priority": "medium",
                "assignee_ids": [self.user_id]
            }
        )
        assert task_response.status_code == 200
        self.task_id = task_response.json()["task_id"]
    
    def test_get_time_entries(self):
        """Test GET /api/time-entries/ returns time entries"""
        response = requests.get(
            f"{BASE_URL}/api/time-entries/",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get time entries failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of time entries"
        
        print(f"✓ Time entries loaded - {len(data)} entries")
    
    def test_create_time_entry(self):
        """Test POST /api/time-entries/ creates a manual time entry"""
        entry_data = {
            "task_id": self.task_id,
            "duration_minutes": 30,
            "description": "Test time entry"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/time-entries/",
            headers=self.headers,
            json=entry_data
        )
        
        assert response.status_code == 200, f"Create time entry failed: {response.text}"
        
        data = response.json()
        assert data["task_id"] == self.task_id
        assert data["duration_minutes"] == 30
        assert "entry_id" in data
        
        print(f"✓ Time entry created: {data['duration_minutes']} minutes (ID: {data['entry_id']})")
    
    def test_get_active_timer(self):
        """Test GET /api/time-entries/timer/active returns timer status"""
        response = requests.get(
            f"{BASE_URL}/api/time-entries/timer/active",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get active timer failed: {response.text}"
        
        data = response.json()
        assert "active" in data
        assert isinstance(data["active"], bool)
        
        print(f"✓ Active timer check - active: {data['active']}")
    
    def test_time_summary(self):
        """Test GET /api/time-entries/summary returns time summary"""
        response = requests.get(
            f"{BASE_URL}/api/time-entries/summary",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get time summary failed: {response.text}"
        
        data = response.json()
        assert "by_user" in data
        assert "by_task" in data
        assert "total_minutes" in data
        assert "total_hours" in data
        
        print(f"✓ Time summary loaded - {data['total_hours']} total hours")


class TestComments:
    """Comments API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and create a test task"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_response.status_code == 200, "Login failed in setup"
        self.token = login_response.json()["access_token"]
        self.user_id = login_response.json()["user"]["user_id"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get org_id
        org_response = requests.get(
            f"{BASE_URL}/api/organizations/",
            headers=self.headers
        )
        assert org_response.status_code == 200
        self.org_id = org_response.json()[0]["org_id"]
        
        # Get or create a project
        projects_response = requests.get(
            f"{BASE_URL}/api/projects/",
            headers=self.headers
        )
        assert projects_response.status_code == 200
        projects = projects_response.json()
        
        if len(projects) > 0:
            self.project_id = projects[0]["project_id"]
        else:
            create_response = requests.post(
                f"{BASE_URL}/api/projects/?org_id={self.org_id}",
                headers=self.headers,
                json={"name": "TEST_CommentProject", "status": "active"}
            )
            assert create_response.status_code == 200
            self.project_id = create_response.json()["project_id"]
        
        # Create a task for comments
        task_response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=self.headers,
            json={
                "project_id": self.project_id,
                "title": f"TEST_CommentTask_{datetime.now().strftime('%H%M%S')}",
                "status": "todo",
                "priority": "medium",
                "assignee_ids": []
            }
        )
        assert task_response.status_code == 200
        self.task_id = task_response.json()["task_id"]
    
    def test_get_comments_by_task(self):
        """Test GET /api/comments/?task_id={task_id} returns task comments"""
        response = requests.get(
            f"{BASE_URL}/api/comments/?task_id={self.task_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get comments failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of comments"
        
        print(f"✓ Comments loaded - {len(data)} comments on task")
    
    def test_create_comment(self):
        """Test POST /api/comments/ creates a new comment"""
        comment_data = {
            "task_id": self.task_id,
            "content": f"Test comment created at {datetime.now().isoformat()}"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comments/",
            headers=self.headers,
            json=comment_data
        )
        
        assert response.status_code == 200, f"Create comment failed: {response.text}"
        
        data = response.json()
        assert data["content"] == comment_data["content"]
        assert data["task_id"] == self.task_id
        assert "comment_id" in data
        assert "author_name" in data
        
        print(f"✓ Comment created by {data['author_name']} (ID: {data['comment_id']})")
    
    def test_get_comments_requires_task_or_project(self):
        """Test GET /api/comments/ without task_id or project_id returns 400"""
        response = requests.get(
            f"{BASE_URL}/api/comments/",
            headers=self.headers
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Comments endpoint correctly requires task_id or project_id")


class TestSubscriptions:
    """Subscription Plans API tests"""
    
    def test_get_subscription_plans(self):
        """Test GET /api/subscriptions/plans returns available plans"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        
        assert response.status_code == 200, f"Get plans failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of plans"
        assert len(data) > 0, "Should have at least one plan"
        
        # Verify plan structure
        plan = data[0]
        assert "plan_id" in plan
        assert "name" in plan
        
        print(f"✓ Subscription plans loaded - {len(data)} plans available")
        
        # Print plan names
        for p in data:
            print(f"  - {p['name']}")


class TestIntegration:
    """Integration tests - full workflows"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_response.status_code == 200, "Login failed in setup"
        self.token = login_response.json()["access_token"]
        self.user_id = login_response.json()["user"]["user_id"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get org_id
        org_response = requests.get(
            f"{BASE_URL}/api/organizations/",
            headers=self.headers
        )
        assert org_response.status_code == 200
        self.org_id = org_response.json()[0]["org_id"]
        
        # Get existing project
        projects_response = requests.get(
            f"{BASE_URL}/api/projects/",
            headers=self.headers
        )
        assert projects_response.status_code == 200
        projects = projects_response.json()
        assert len(projects) > 0, "Need at least one project for integration tests"
        self.project_id = projects[0]["project_id"]
        self.project_name = projects[0]["name"]
    
    def test_full_task_workflow(self):
        """Test complete workflow: Create Task -> Add Comment -> Log Time -> Update Status"""
        # 1. Create Task in existing project
        task_data = {
            "project_id": self.project_id,
            "title": f"TEST_Workflow_Task_{datetime.now().strftime('%H%M%S')}",
            "description": "Task for integration test",
            "status": "todo",
            "priority": "high",
            "assignee_ids": [self.user_id]
        }
        
        task_response = requests.post(
            f"{BASE_URL}/api/tasks/",
            headers=self.headers,
            json=task_data
        )
        assert task_response.status_code == 200, f"Create task failed: {task_response.text}"
        task_id = task_response.json()["task_id"]
        print(f"  1. Created task: {task_data['title']} in project {self.project_name}")
        
        # 2. Add Comment
        comment_data = {
            "task_id": task_id,
            "content": "Starting work on this task"
        }
        
        comment_response = requests.post(
            f"{BASE_URL}/api/comments/",
            headers=self.headers,
            json=comment_data
        )
        assert comment_response.status_code == 200, f"Create comment failed: {comment_response.text}"
        print(f"  2. Added comment to task")
        
        # 3. Log Time
        time_data = {
            "task_id": task_id,
            "duration_minutes": 45,
            "description": "Initial work"
        }
        
        time_response = requests.post(
            f"{BASE_URL}/api/time-entries/",
            headers=self.headers,
            json=time_data
        )
        assert time_response.status_code == 200, f"Create time entry failed: {time_response.text}"
        print(f"  3. Logged {time_data['duration_minutes']} minutes")
        
        # 4. Update Task Status
        update_response = requests.put(
            f"{BASE_URL}/api/tasks/{task_id}",
            headers=self.headers,
            json={"status": "in_progress"}
        )
        assert update_response.status_code == 200, f"Update task failed: {update_response.text}"
        print(f"  4. Updated task status to in_progress")
        
        # 5. Verify in Dashboard
        dashboard_response = requests.get(
            f"{BASE_URL}/api/dashboard/",
            headers=self.headers
        )
        assert dashboard_response.status_code == 200
        print(f"  5. Verified in dashboard")
        
        # 6. Search for the task
        search_response = requests.get(
            f"{BASE_URL}/api/search/?q=Workflow",
            headers=self.headers
        )
        assert search_response.status_code == 200
        search_results = search_response.json()
        print(f"  6. Search completed - {search_results['total']} results")
        
        # 7. Get task comments
        comments_response = requests.get(
            f"{BASE_URL}/api/comments/?task_id={task_id}",
            headers=self.headers
        )
        assert comments_response.status_code == 200
        comments = comments_response.json()
        assert len(comments) >= 1, "Should have at least one comment"
        print(f"  7. Verified comments - {len(comments)} comments on task")
        
        # 8. Get time entries for task
        time_entries_response = requests.get(
            f"{BASE_URL}/api/time-entries/?task_id={task_id}",
            headers=self.headers
        )
        assert time_entries_response.status_code == 200
        entries = time_entries_response.json()
        assert len(entries) >= 1, "Should have at least one time entry"
        print(f"  8. Verified time entries - {len(entries)} entries")
        
        print("✓ Full workflow completed successfully!")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
