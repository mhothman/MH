"""
Locust Load Testing Configuration for ProFlow
Run with: locust -f tests/locustfile.py --host=<BACKEND_URL>

Example:
  locust -f tests/locustfile.py --host=https://costmanager-5.preview.emergentagent.com

Then open http://localhost:8089 for the Locust web interface.
"""
import os
from locust import HttpUser, task, between

# Test credentials
SUPER_ADMIN_EMAIL = "test@proflow.com"
SUPER_ADMIN_PASSWORD = "test123456"


class ProFlowUser(HttpUser):
    """Simulated user for load testing"""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login when user starts"""
        response = self.client.post("/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            # Get org_id for subsequent requests
            orgs = self.client.get("/api/organizations/", headers=self.headers)
            if orgs.status_code == 200 and orgs.json():
                self.org_id = orgs.json()[0]["org_id"]
        else:
            self.token = None
            self.headers = {}
            self.org_id = None
    
    @task(10)
    def get_tasks(self):
        """Get all tasks - Most common operation"""
        self.client.get("/api/tasks/", headers=self.headers)
    
    @task(5)
    def get_projects(self):
        """Get all projects"""
        self.client.get("/api/projects/", headers=self.headers)
    
    @task(3)
    def get_notifications(self):
        """Get notifications"""
        self.client.get("/api/notifications/", headers=self.headers)
    
    @task(2)
    def get_organization_members(self):
        """Get org members"""
        if self.org_id:
            self.client.get(f"/api/organizations/{self.org_id}/members", headers=self.headers)
    
    @task(1)
    def get_time_summary(self):
        """Get time summary"""
        self.client.get("/api/time-entries/summary", headers=self.headers)


class ProjectManagerUser(HttpUser):
    """Simulated project manager performing write operations"""
    
    wait_time = between(2, 5)
    
    def on_start(self):
        """Login when user starts"""
        response = self.client.post("/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            # Get project for tasks
            projects = self.client.get("/api/projects/", headers=self.headers)
            if projects.status_code == 200 and projects.json():
                self.project_id = projects.json()[0]["project_id"]
            else:
                self.project_id = None
            # Get tasks
            tasks = self.client.get("/api/tasks/", headers=self.headers)
            if tasks.status_code == 200 and tasks.json():
                self.task_ids = [t["task_id"] for t in tasks.json()[:5]]
            else:
                self.task_ids = []
        else:
            self.token = None
            self.headers = {}
            self.project_id = None
            self.task_ids = []
    
    @task(5)
    def view_dashboard(self):
        """View dashboard data"""
        self.client.get("/api/dashboard/overview", headers=self.headers)
    
    @task(3)
    def view_task_details(self):
        """View task details"""
        if self.task_ids:
            import random
            task_id = random.choice(self.task_ids)
            self.client.get(f"/api/tasks/{task_id}", headers=self.headers)
    
    @task(2)
    def update_task_priority(self):
        """Update task priority"""
        if self.task_ids:
            import random
            task_id = random.choice(self.task_ids)
            priority = random.choice(["low", "medium", "high"])
            self.client.put(
                f"/api/tasks/{task_id}",
                json={"priority": priority},
                headers=self.headers
            )
    
    @task(1)
    def create_time_entry(self):
        """Create a time entry"""
        if self.task_ids:
            import random
            task_id = random.choice(self.task_ids)
            self.client.post(
                "/api/time-entries/",
                json={
                    "task_id": task_id,
                    "duration_minutes": random.randint(15, 120),
                    "description": "Load test time entry"
                },
                headers=self.headers
            )
