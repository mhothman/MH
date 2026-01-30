import requests
import sys
import json
from datetime import datetime

class ProFlowAPITester:
    def __init__(self, base_url="https://costmanager-5.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_data = None
        self.org_id = None
        self.project_id = None
        self.task_id = None
        self.checklist_item_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json()
                    self.log_test(name, True)
                    return True, response_data
                except:
                    self.log_test(name, True, "No JSON response")
                    return True, {}
            else:
                error_msg = f"Expected {expected_status}, got {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('detail', '')}"
                except:
                    error_msg += f" - {response.text[:100]}"
                
                self.log_test(name, False, error_msg)
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health endpoint"""
        return self.run_test("Health Check", "GET", "", 200)

    def test_register(self):
        """Test user registration"""
        test_user_data = {
            "email": "test@proflow.com",
            "password": "test123456",
            "name": "Test User"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=test_user_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response.get('user', {})
            return True
        return False

    def test_login(self):
        """Test user login"""
        login_data = {
            "email": "test@proflow.com",
            "password": "test123456"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response.get('user', {})
            return True
        return False

    def test_get_me(self):
        """Test get current user"""
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        return success

    def test_get_organizations(self):
        """Test get organizations"""
        success, response = self.run_test(
            "Get Organizations",
            "GET",
            "organizations/",
            200
        )
        
        if success and isinstance(response, list) and len(response) > 0:
            self.org_id = response[0].get('org_id')
            return True
        return success

    def test_dashboard(self):
        """Test dashboard endpoint"""
        success, response = self.run_test(
            "Get Dashboard",
            "GET",
            "dashboard",
            200
        )
        return success

    def test_create_project(self):
        """Test project creation"""
        if not self.org_id:
            self.log_test("Create Project", False, "No organization ID available")
            return False
            
        project_data = {
            "name": "Test Project",
            "description": "A test project for API testing",
            "status": "active",
            "color": "#3B82F6"
        }
        
        success, response = self.run_test(
            "Create Project",
            "POST",
            f"projects/?org_id={self.org_id}",
            200,
            data=project_data
        )
        
        if success and 'project_id' in response:
            self.project_id = response['project_id']
            return True
        return False

    def test_get_projects(self):
        """Test get projects"""
        success, response = self.run_test(
            "Get Projects",
            "GET",
            "projects/",
            200
        )
        return success

    def test_get_project_detail(self):
        """Test get project by ID"""
        if not self.project_id:
            self.log_test("Get Project Detail", False, "No project ID available")
            return False
            
        success, response = self.run_test(
            "Get Project Detail",
            "GET",
            f"projects/{self.project_id}",
            200
        )
        return success

    def test_create_task(self):
        """Test task creation"""
        if not self.project_id:
            self.log_test("Create Task", False, "No project ID available")
            return False
            
        task_data = {
            "title": "Test Task",
            "description": "A test task for API testing",
            "project_id": self.project_id,
            "status": "todo",
            "priority": "medium"
        }
        
        success, response = self.run_test(
            "Create Task",
            "POST",
            "tasks/",
            200,
            data=task_data
        )
        
        if success and 'task_id' in response:
            self.task_id = response['task_id']
            return True
        return False

    def test_get_tasks(self):
        """Test get tasks"""
        success, response = self.run_test(
            "Get Tasks",
            "GET",
            f"tasks/?project_id={self.project_id}" if self.project_id else "tasks/",
            200
        )
        return success

    def test_update_task_status(self):
        """Test task status update"""
        if not self.task_id:
            self.log_test("Update Task Status", False, "No task ID available")
            return False
            
        update_data = {
            "status": "in_progress"
        }
        
        success, response = self.run_test(
            "Update Task Status",
            "PUT",
            f"tasks/{self.task_id}",
            200,
            data=update_data
        )
        return success

    def test_create_comment(self):
        """Test comment creation"""
        if not self.task_id:
            self.log_test("Create Comment", False, "No task ID available")
            return False
            
        comment_data = {
            "content": "This is a test comment",
            "task_id": self.task_id
        }
        
        success, response = self.run_test(
            "Create Comment",
            "POST",
            "comments/",
            200,
            data=comment_data
        )
        return success

    def test_get_comments(self):
        """Test get comments"""
        if not self.task_id:
            self.log_test("Get Comments", False, "No task ID available")
            return False
            
        success, response = self.run_test(
            "Get Comments",
            "GET",
            f"comments/?task_id={self.task_id}",
            200
        )
        return success

    def test_start_timer(self):
        """Test start timer"""
        if not self.task_id:
            self.log_test("Start Timer", False, "No task ID available")
            return False
            
        timer_data = {
            "task_id": self.task_id,
            "description": "Testing timer functionality"
        }
        
        success, response = self.run_test(
            "Start Timer",
            "POST",
            "time-entries/timer/start",
            200,
            data=timer_data
        )
        return success

    def test_get_active_timer(self):
        """Test get active timer"""
        success, response = self.run_test(
            "Get Active Timer",
            "GET",
            "time-entries/timer/active",
            200
        )
        return success

    def test_stop_timer(self):
        """Test stop timer"""
        success, response = self.run_test(
            "Stop Timer",
            "POST",
            "time-entries/timer/stop",
            200
        )
        return success

    def test_add_checklist_item(self):
        """Test add checklist item"""
        if not self.task_id:
            self.log_test("Add Checklist Item", False, "No task ID available")
            return False
            
        checklist_data = {
            "title": "Test checklist item",
            "completed": False
        }
        
        success, response = self.run_test(
            "Add Checklist Item",
            "POST",
            f"tasks/{self.task_id}/checklist",
            200,
            data=checklist_data
        )
        
        if success and 'item_id' in response:
            self.checklist_item_id = response['item_id']
            return True
        return success

    def test_update_checklist_item(self):
        """Test update checklist item"""
        if not self.task_id or not hasattr(self, 'checklist_item_id'):
            self.log_test("Update Checklist Item", False, "No task ID or checklist item ID available")
            return False
            
        update_data = {
            "completed": True
        }
        
        success, response = self.run_test(
            "Update Checklist Item",
            "PUT",
            f"tasks/{self.task_id}/checklist/{self.checklist_item_id}",
            200,
            data=update_data
        )
        return success

    def test_delete_checklist_item(self):
        """Test delete checklist item"""
        if not self.task_id or not hasattr(self, 'checklist_item_id'):
            self.log_test("Delete Checklist Item", False, "No task ID or checklist item ID available")
            return False
            
        success, response = self.run_test(
            "Delete Checklist Item",
            "DELETE",
            f"tasks/{self.task_id}/checklist/{self.checklist_item_id}",
            200
        )
        return success

    def test_export_tasks_json(self):
        """Test export tasks as JSON"""
        if not self.org_id:
            self.log_test("Export Tasks JSON", False, "No organization ID available")
            return False
            
        success, response = self.run_test(
            "Export Tasks JSON",
            "GET",
            f"reports/export/tasks?org_id={self.org_id}&format=json",
            200
        )
        return success

    def test_export_tasks_csv(self):
        """Test export tasks as CSV"""
        if not self.org_id:
            self.log_test("Export Tasks CSV", False, "No organization ID available")
            return False
            
        # For CSV, we expect a different response type
        url = f"{self.base_url}/api/reports/export/tasks?org_id={self.org_id}&format=csv"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            success = response.status_code == 200
            
            if success:
                self.log_test("Export Tasks CSV", True)
                return True
            else:
                self.log_test("Export Tasks CSV", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Export Tasks CSV", False, f"Exception: {str(e)}")
            return False

    def test_export_time_json(self):
        """Test export time report as JSON"""
        if not self.org_id:
            self.log_test("Export Time JSON", False, "No organization ID available")
            return False
            
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        success, response = self.run_test(
            "Export Time JSON",
            "GET",
            f"reports/export/time?org_id={self.org_id}&start_date={start_date}&end_date={end_date}&format=json",
            200
        )
        return success

    def test_export_time_csv(self):
        """Test export time report as CSV"""
        if not self.org_id:
            self.log_test("Export Time CSV", False, "No organization ID available")
            return False
            
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        url = f"{self.base_url}/api/reports/export/time?org_id={self.org_id}&start_date={start_date}&end_date={end_date}&format=csv"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            success = response.status_code == 200
            
            if success:
                self.log_test("Export Time CSV", True)
                return True
            else:
                self.log_test("Export Time CSV", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Export Time CSV", False, f"Exception: {str(e)}")
            return False

    def test_logout(self):
        """Test logout"""
        success, response = self.run_test(
            "Logout",
            "POST",
            "auth/logout",
            200
        )
        return success

def main():
    print("🚀 Starting ProFlow API Tests...")
    print("=" * 50)
    
    tester = ProFlowAPITester()
    
    # Test sequence
    test_sequence = [
        ("Health Check", tester.test_health_check),
        ("User Login", tester.test_login),
        ("Get Current User", tester.test_get_me),
        ("Get Organizations", tester.test_get_organizations),
        ("Dashboard", tester.test_dashboard),
        ("Create Project", tester.test_create_project),
        ("Get Projects", tester.test_get_projects),
        ("Get Project Detail", tester.test_get_project_detail),
        ("Create Task", tester.test_create_task),
        ("Get Tasks", tester.test_get_tasks),
        ("Update Task Status", tester.test_update_task_status),
        ("Start Timer", tester.test_start_timer),
        ("Get Active Timer", tester.test_get_active_timer),
        ("Stop Timer", tester.test_stop_timer),
        ("Add Checklist Item", tester.test_add_checklist_item),
        ("Update Checklist Item", tester.test_update_checklist_item),
        ("Delete Checklist Item", tester.test_delete_checklist_item),
        ("Export Tasks JSON", tester.test_export_tasks_json),
        ("Export Tasks CSV", tester.test_export_tasks_csv),
        ("Export Time JSON", tester.test_export_time_json),
        ("Export Time CSV", tester.test_export_time_csv),
        ("Create Comment", tester.test_create_comment),
        ("Get Comments", tester.test_get_comments),
        ("Logout", tester.test_logout),
    ]
    
    # Run all tests
    for test_name, test_func in test_sequence:
        print(f"\n🔍 Running: {test_name}")
        try:
            test_func()
        except Exception as e:
            tester.log_test(test_name, False, f"Exception: {str(e)}")
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results Summary:")
    print(f"   Total Tests: {tester.tests_run}")
    print(f"   Passed: {tester.tests_passed}")
    print(f"   Failed: {tester.tests_run - tester.tests_passed}")
    print(f"   Success Rate: {(tester.tests_passed / tester.tests_run * 100):.1f}%" if tester.tests_run > 0 else "0%")
    
    # Save detailed results
    results = {
        "summary": {
            "total_tests": tester.tests_run,
            "passed_tests": tester.tests_passed,
            "failed_tests": tester.tests_run - tester.tests_passed,
            "success_rate": (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0,
            "timestamp": datetime.now().isoformat()
        },
        "test_details": tester.test_results,
        "user_data": tester.user_data,
        "org_id": tester.org_id,
        "project_id": tester.project_id,
        "task_id": tester.task_id
    }
    
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /app/backend_test_results.json")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())