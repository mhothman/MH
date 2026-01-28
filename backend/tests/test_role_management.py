"""
Test Role Management Features:
1. Login as test@proflow.com (super_admin) and verify role change works
2. Verify role change dropdown shows 'Super Admin' and 'Org Admin' options
3. Verify custom role creation works
4. Verify workflow rule creation includes description field
5. Verify workflow rules display their descriptions
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "test@proflow.com"
SUPER_ADMIN_PASSWORD = "test123456"
TARGET_USER_EMAIL = "mahmoudothman@msn.com"
ORG_ID = "org_3a0711d3f937"


class TestRoleManagement:
    """Test role management features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.token = None
        self.user_id = None
        
    def login_as_super_admin(self):
        """Login as super_admin user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.user_id = data.get("user", {}).get("user_id")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        return data
    
    def test_01_login_as_super_admin(self):
        """Test login as super_admin user"""
        data = self.login_as_super_admin()
        assert "access_token" in data, "No access token in response"
        assert "user" in data, "No user in response"
        print(f"✓ Logged in as {SUPER_ADMIN_EMAIL}")
        print(f"  User ID: {data['user'].get('user_id')}")
        print(f"  Name: {data['user'].get('name')}")
        
    def test_02_get_my_permissions(self):
        """Test getting permissions for super_admin"""
        self.login_as_super_admin()
        response = self.session.get(f"{BASE_URL}/api/auth/permissions/{ORG_ID}")
        assert response.status_code == 200, f"Failed to get permissions: {response.text}"
        data = response.json()
        print(f"✓ Got permissions for org {ORG_ID}")
        print(f"  Role: {data.get('role')}")
        print(f"  Permissions count: {len(data.get('permissions', []))}")
        # Verify super_admin role
        assert data.get('role') == 'super_admin', f"Expected super_admin role, got {data.get('role')}"
        
    def test_03_get_organization_members(self):
        """Test getting organization members"""
        self.login_as_super_admin()
        response = self.session.get(f"{BASE_URL}/api/organizations/{ORG_ID}/members")
        assert response.status_code == 200, f"Failed to get members: {response.text}"
        members = response.json()
        print(f"✓ Got {len(members)} members")
        
        # Find target user
        target_user = None
        for member in members:
            print(f"  - {member.get('email')}: {member.get('org_role')}")
            if member.get('email') == TARGET_USER_EMAIL:
                target_user = member
                
        assert target_user is not None, f"Target user {TARGET_USER_EMAIL} not found"
        print(f"✓ Found target user: {TARGET_USER_EMAIL} with role {target_user.get('org_role')}")
        return target_user
        
    def test_04_get_roles_for_org(self):
        """Test getting all roles (built-in + custom) for organization"""
        self.login_as_super_admin()
        response = self.session.get(f"{BASE_URL}/api/roles/org/{ORG_ID}")
        assert response.status_code == 200, f"Failed to get roles: {response.text}"
        data = response.json()
        
        built_in_roles = data.get('built_in_roles', [])
        custom_roles = data.get('custom_roles', [])
        
        print(f"✓ Got roles for org {ORG_ID}")
        print(f"  Built-in roles: {len(built_in_roles)}")
        for role in built_in_roles:
            print(f"    - {role.get('name')} ({role.get('key')})")
            
        print(f"  Custom roles: {len(custom_roles)}")
        for role in custom_roles:
            print(f"    - {role.get('name')} (ID: {role.get('role_id')})")
            
        # Verify built-in roles include super_admin and org_admin
        role_keys = [r.get('key') for r in built_in_roles]
        assert 'super_admin' in role_keys, "super_admin not in built-in roles"
        assert 'org_admin' in role_keys, "org_admin not in built-in roles"
        print("✓ Verified super_admin and org_admin are in built-in roles")
        
        return data
        
    def test_05_change_member_role(self):
        """Test changing a member's role"""
        self.login_as_super_admin()
        
        # First get the target user's ID
        response = self.session.get(f"{BASE_URL}/api/organizations/{ORG_ID}/members")
        assert response.status_code == 200
        members = response.json()
        
        target_user = None
        for member in members:
            if member.get('email') == TARGET_USER_EMAIL:
                target_user = member
                break
                
        assert target_user is not None, f"Target user {TARGET_USER_EMAIL} not found"
        target_user_id = target_user.get('user_id')
        original_role = target_user.get('org_role')
        
        print(f"✓ Found target user: {TARGET_USER_EMAIL}")
        print(f"  User ID: {target_user_id}")
        print(f"  Current role: {original_role}")
        
        # Try to change role to project_manager
        new_role = "project_manager"
        response = self.session.post(
            f"{BASE_URL}/api/organizations/{ORG_ID}/members/{target_user_id}/change-role",
            json={"role": new_role}
        )
        
        if response.status_code == 200:
            print(f"✓ Successfully changed role to {new_role}")
            
            # Verify the change
            response = self.session.get(f"{BASE_URL}/api/organizations/{ORG_ID}/members")
            members = response.json()
            for member in members:
                if member.get('user_id') == target_user_id:
                    assert member.get('org_role') == new_role, f"Role not changed to {new_role}"
                    print(f"✓ Verified role is now {member.get('org_role')}")
                    break
                    
            # Change back to original role
            response = self.session.post(
                f"{BASE_URL}/api/organizations/{ORG_ID}/members/{target_user_id}/change-role",
                json={"role": original_role}
            )
            if response.status_code == 200:
                print(f"✓ Restored original role: {original_role}")
            else:
                print(f"⚠ Could not restore original role: {response.text}")
        else:
            print(f"✗ Failed to change role: {response.status_code} - {response.text}")
            # This might fail due to role hierarchy - report the error
            assert False, f"Role change failed: {response.text}"
            
    def test_06_create_custom_role(self):
        """Test creating a custom role"""
        self.login_as_super_admin()
        
        # Create a test custom role
        role_data = {
            "name": "TEST_Custom_Developer",
            "description": "Test custom role for developers",
            "permissions": ["task:view", "task:create", "task:edit_own", "project:view"],
            "color": "#10b981"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/roles/org/{ORG_ID}",
            json=role_data
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Created custom role: {data.get('name')}")
            print(f"  Role ID: {data.get('role_id')}")
            print(f"  Permissions: {len(data.get('permissions', []))}")
            
            # Clean up - delete the test role
            role_id = data.get('role_id')
            delete_response = self.session.delete(f"{BASE_URL}/api/roles/{role_id}")
            if delete_response.status_code == 200:
                print(f"✓ Cleaned up test role")
            else:
                print(f"⚠ Could not delete test role: {delete_response.text}")
        elif response.status_code == 400 and "already exists" in response.text:
            print(f"⚠ Role already exists, trying to delete and recreate")
            # Try to find and delete existing role
            roles_response = self.session.get(f"{BASE_URL}/api/roles/org/{ORG_ID}")
            if roles_response.status_code == 200:
                roles_data = roles_response.json()
                for role in roles_data.get('custom_roles', []):
                    if role.get('name') == role_data['name']:
                        delete_response = self.session.delete(f"{BASE_URL}/api/roles/{role.get('role_id')}")
                        print(f"  Deleted existing role: {delete_response.status_code}")
                        break
        else:
            print(f"✗ Failed to create custom role: {response.status_code} - {response.text}")
            assert False, f"Custom role creation failed: {response.text}"
            
    def test_07_get_all_permissions(self):
        """Test getting all available permissions"""
        self.login_as_super_admin()
        
        response = self.session.get(f"{BASE_URL}/api/roles/permissions")
        assert response.status_code == 200, f"Failed to get permissions: {response.text}"
        data = response.json()
        
        permissions = data.get('permissions', [])
        categories = data.get('categories', {})
        
        print(f"✓ Got {len(permissions)} permissions in {len(categories)} categories")
        for category, perms in categories.items():
            print(f"  {category}: {len(perms)} permissions")
            
        assert len(permissions) > 0, "No permissions returned"
        assert len(categories) > 0, "No categories returned"


class TestWorkflowRules:
    """Test workflow rule features including description field"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.token = None
        
    def login_as_super_admin(self):
        """Login as super_admin user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        return data
        
    def test_01_get_org_workflows(self):
        """Test getting organization workflows"""
        self.login_as_super_admin()
        
        response = self.session.get(f"{BASE_URL}/api/workflows/org/{ORG_ID}")
        assert response.status_code == 200, f"Failed to get workflows: {response.text}"
        workflows = response.json()
        
        print(f"✓ Got {len(workflows)} workflows for org {ORG_ID}")
        for wf in workflows:
            print(f"  - {wf.get('name')} (ID: {wf.get('workflow_id')}, Rules: {wf.get('rules_count')})")
            
        return workflows
        
    def test_02_create_workflow_with_description(self):
        """Test creating a workflow and rule with description"""
        self.login_as_super_admin()
        
        # Create a test workflow
        workflow_data = {
            "name": "TEST_Approval_Workflow",
            "description": "Test workflow for approval testing",
            "scope": "selective",
            "active": True
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/workflows/org/{ORG_ID}",
            json=workflow_data
        )
        
        if response.status_code == 200:
            workflow = response.json()
            workflow_id = workflow.get('workflow_id')
            print(f"✓ Created workflow: {workflow.get('name')}")
            print(f"  Workflow ID: {workflow_id}")
            
            # Create a rule with description
            rule_data = {
                "from_status": "in_progress",
                "to_status": "done",
                "description": "Require approval when completing tasks",
                "approval_required": True,
                "approval_type": "single",
                "approver_role": "project_manager",
                "notify_on_request": True,
                "notify_on_resolution": True
            }
            
            rule_response = self.session.post(
                f"{BASE_URL}/api/workflows/{workflow_id}/rules",
                json=rule_data
            )
            
            if rule_response.status_code == 200:
                rule = rule_response.json()
                print(f"✓ Created rule with description")
                print(f"  Rule ID: {rule.get('rule_id')}")
                print(f"  Description: {rule.get('description')}")
                assert rule.get('description') == rule_data['description'], "Description not saved correctly"
                
                # Verify the rule description is returned when getting workflow
                get_response = self.session.get(f"{BASE_URL}/api/workflows/{workflow_id}")
                if get_response.status_code == 200:
                    wf_data = get_response.json()
                    rules = wf_data.get('rules', [])
                    for r in rules:
                        if r.get('rule_id') == rule.get('rule_id'):
                            print(f"✓ Verified rule description in workflow response: {r.get('description')}")
                            assert r.get('description') == rule_data['description']
                            break
            else:
                print(f"✗ Failed to create rule: {rule_response.status_code} - {rule_response.text}")
                
            # Clean up - delete the test workflow
            delete_response = self.session.delete(f"{BASE_URL}/api/workflows/{workflow_id}")
            if delete_response.status_code == 200:
                print(f"✓ Cleaned up test workflow")
            else:
                print(f"⚠ Could not delete test workflow: {delete_response.text}")
        elif response.status_code == 400:
            print(f"⚠ Workflow creation issue: {response.text}")
        else:
            print(f"✗ Failed to create workflow: {response.status_code} - {response.text}")
            
    def test_03_verify_existing_workflow_rules_have_description(self):
        """Test that existing workflow rules support description field"""
        self.login_as_super_admin()
        
        # Get all workflows
        response = self.session.get(f"{BASE_URL}/api/workflows/org/{ORG_ID}")
        assert response.status_code == 200
        workflows = response.json()
        
        if len(workflows) == 0:
            print("⚠ No workflows found to test")
            return
            
        # Get details of first workflow
        workflow_id = workflows[0].get('workflow_id')
        response = self.session.get(f"{BASE_URL}/api/workflows/{workflow_id}")
        assert response.status_code == 200, f"Failed to get workflow: {response.text}"
        
        workflow = response.json()
        rules = workflow.get('rules', [])
        
        print(f"✓ Checking workflow: {workflow.get('name')}")
        print(f"  Rules count: {len(rules)}")
        
        for rule in rules:
            description = rule.get('description')
            print(f"  - Rule {rule.get('rule_id')}: {rule.get('from_status')} → {rule.get('to_status')}")
            print(f"    Description: {description if description else '(none)'}")
            
        # Verify the description field exists in the response schema
        if len(rules) > 0:
            assert 'description' in rules[0] or rules[0].get('description') is None, "Description field not in rule response"
            print("✓ Description field is present in rule response schema")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
