"""
Test suite for Real-time Notifications feature
Tests: Notification preferences, notification CRUD, paginated notifications, mark as read
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_SUPER_ADMIN = {"email": "test@proflow.com", "password": "test123456"}
TEST_TEAM_MEMBER = {"email": "ahmed@ahmed.com", "password": "Su@12345"}


class TestNotificationAPIs:
    """Test notification API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as super admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=TEST_SUPER_ADMIN)
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        self.token = data.get("access_token")
        self.user_id = data.get("user", {}).get("user_id")
        
        assert self.token, "No token received"
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        self.session.close()
    
    # ==================== Notification Preferences Tests ====================
    
    def test_get_notification_preferences(self):
        """Test GET /api/notifications/preferences - returns user preferences"""
        response = self.session.get(f"{BASE_URL}/api/notifications/preferences")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "user_id" in data, "Missing user_id in response"
        assert "email_notifications_enabled" in data, "Missing email_notifications_enabled"
        assert "browser_push_enabled" in data, "Missing browser_push_enabled"
        assert "quiet_hours_enabled" in data, "Missing quiet_hours_enabled"
        assert "preferences" in data, "Missing preferences dict"
        
        # Verify preferences is a dict with notification types
        assert isinstance(data["preferences"], dict), "preferences should be a dict"
        
        print(f"SUCCESS: Got notification preferences for user {data['user_id']}")
        print(f"  - Email notifications: {data['email_notifications_enabled']}")
        print(f"  - Quiet hours: {data['quiet_hours_enabled']}")
        print(f"  - Preference types count: {len(data['preferences'])}")
    
    def test_update_notification_preferences(self):
        """Test PUT /api/notifications/preferences - updates user preferences"""
        update_payload = {
            "email_notifications_enabled": False,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00",
            "quiet_hours_end": "07:00",
            "preferences": {
                "task_assigned": {
                    "enabled": True,
                    "channels": ["in_app", "email"]
                },
                "task_status_changed": {
                    "enabled": False,
                    "channels": ["in_app"]
                }
            }
        }
        
        response = self.session.put(
            f"{BASE_URL}/api/notifications/preferences",
            json=update_payload
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # Verify updates were applied
        assert data["email_notifications_enabled"] == False, "email_notifications_enabled not updated"
        assert data["quiet_hours_enabled"] == True, "quiet_hours_enabled not updated"
        assert data["quiet_hours_start"] == "23:00", "quiet_hours_start not updated"
        assert data["quiet_hours_end"] == "07:00", "quiet_hours_end not updated"
        
        print("SUCCESS: Updated notification preferences")
        print(f"  - Email notifications: {data['email_notifications_enabled']}")
        print(f"  - Quiet hours: {data['quiet_hours_start']} - {data['quiet_hours_end']}")
        
        # Reset preferences back to defaults
        reset_payload = {
            "email_notifications_enabled": True,
            "quiet_hours_enabled": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00"
        }
        self.session.put(f"{BASE_URL}/api/notifications/preferences", json=reset_payload)
    
    # ==================== Notification Types Tests ====================
    
    def test_get_notification_types(self):
        """Test GET /api/notifications/types - returns all notification types"""
        response = self.session.get(f"{BASE_URL}/api/notifications/types")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "types" in data, "Missing types in response"
        assert "categories" in data, "Missing categories in response"
        
        # Verify types dict has expected notification types
        types = data["types"]
        expected_types = [
            "task_assigned", "task_status_changed", "task_due_soon", "task_overdue",
            "document_approval_requested", "document_approved", "document_rejected",
            "project_member_added", "project_member_removed",
            "approval_requested", "approval_approved", "approval_rejected"
        ]
        
        for expected_type in expected_types:
            assert expected_type in types, f"Missing notification type: {expected_type}"
            assert "label" in types[expected_type], f"Missing label for {expected_type}"
            assert "description" in types[expected_type], f"Missing description for {expected_type}"
            assert "category" in types[expected_type], f"Missing category for {expected_type}"
        
        # Verify categories
        categories = data["categories"]
        expected_categories = ["Tasks", "Documents", "Projects", "Approvals", "System"]
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
        
        print(f"SUCCESS: Got {len(types)} notification types in {len(categories)} categories")
        for cat, items in categories.items():
            print(f"  - {cat}: {len(items)} types")
    
    # ==================== Paginated Notifications Tests ====================
    
    def test_get_notifications_paginated(self):
        """Test GET /api/notifications/paginated - returns paginated notifications"""
        response = self.session.get(
            f"{BASE_URL}/api/notifications/paginated",
            params={"page": 1, "page_size": 10}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "notifications" in data, "Missing notifications array"
        assert "total" in data, "Missing total count"
        assert "page" in data, "Missing page number"
        assert "page_size" in data, "Missing page_size"
        assert "has_more" in data, "Missing has_more flag"
        
        assert isinstance(data["notifications"], list), "notifications should be a list"
        assert data["page"] == 1, "Page should be 1"
        assert data["page_size"] == 10, "Page size should be 10"
        
        print(f"SUCCESS: Got paginated notifications")
        print(f"  - Total: {data['total']}")
        print(f"  - Page: {data['page']}/{(data['total'] // data['page_size']) + 1}")
        print(f"  - Has more: {data['has_more']}")
        
        # Verify notification structure if any exist
        if data["notifications"]:
            notif = data["notifications"][0]
            assert "notification_id" in notif, "Missing notification_id"
            assert "type" in notif, "Missing type"
            assert "title" in notif, "Missing title"
            assert "message" in notif, "Missing message"
            assert "read" in notif, "Missing read flag"
            assert "created_at" in notif, "Missing created_at"
            print(f"  - First notification: {notif['title']}")
    
    def test_get_notifications_paginated_unread_only(self):
        """Test GET /api/notifications/paginated with unread_only filter"""
        response = self.session.get(
            f"{BASE_URL}/api/notifications/paginated",
            params={"page": 1, "page_size": 20, "unread_only": True}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # All returned notifications should be unread
        for notif in data["notifications"]:
            assert notif["read"] == False, f"Notification {notif['notification_id']} should be unread"
        
        print(f"SUCCESS: Got {len(data['notifications'])} unread notifications")
    
    def test_get_notifications_paginated_by_type(self):
        """Test GET /api/notifications/paginated with type filter"""
        response = self.session.get(
            f"{BASE_URL}/api/notifications/paginated",
            params={"page": 1, "page_size": 20, "notification_type": "task_assigned"}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # All returned notifications should be of the specified type
        for notif in data["notifications"]:
            assert notif["type"] == "task_assigned", f"Notification type should be task_assigned"
        
        print(f"SUCCESS: Got {len(data['notifications'])} task_assigned notifications")
    
    # ==================== Unread Count Tests ====================
    
    def test_get_unread_count(self):
        """Test GET /api/notifications/unread-count - returns unread count"""
        response = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "count" in data, "Missing count in response"
        assert isinstance(data["count"], int), "count should be an integer"
        assert data["count"] >= 0, "count should be non-negative"
        
        print(f"SUCCESS: Unread notification count: {data['count']}")
    
    # ==================== Mark as Read Tests ====================
    
    def test_mark_notification_read(self):
        """Test PUT /api/notifications/{id}/read - marks notification as read"""
        # First get a notification to mark as read
        response = self.session.get(
            f"{BASE_URL}/api/notifications/paginated",
            params={"page": 1, "page_size": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if not data["notifications"]:
            pytest.skip("No notifications to test mark as read")
        
        notification_id = data["notifications"][0]["notification_id"]
        
        # Mark as read
        response = self.session.put(f"{BASE_URL}/api/notifications/{notification_id}/read")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        result = response.json()
        assert "message" in result, "Missing message in response"
        
        print(f"SUCCESS: Marked notification {notification_id} as read")
    
    def test_mark_notification_read_not_found(self):
        """Test PUT /api/notifications/{id}/read with invalid ID - returns 404"""
        fake_id = f"notif_{uuid.uuid4().hex[:12]}"
        
        response = self.session.put(f"{BASE_URL}/api/notifications/{fake_id}/read")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"SUCCESS: Got 404 for non-existent notification {fake_id}")
    
    def test_mark_all_notifications_read(self):
        """Test PUT /api/notifications/read-all - marks all notifications as read"""
        response = self.session.put(f"{BASE_URL}/api/notifications/read-all")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Missing message in response"
        assert "count" in data, "Missing count in response"
        
        print(f"SUCCESS: Marked {data['count']} notifications as read")
        
        # Verify all are now read
        verify_response = self.session.get(
            f"{BASE_URL}/api/notifications/paginated",
            params={"page": 1, "page_size": 100, "unread_only": True}
        )
        verify_data = verify_response.json()
        assert len(verify_data["notifications"]) == 0, "Should have no unread notifications"
    
    # ==================== Delete Notification Tests ====================
    
    def test_delete_notification(self):
        """Test DELETE /api/notifications/{id} - deletes a notification"""
        # First get a notification to delete
        response = self.session.get(
            f"{BASE_URL}/api/notifications/paginated",
            params={"page": 1, "page_size": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if not data["notifications"]:
            pytest.skip("No notifications to test delete")
        
        notification_id = data["notifications"][0]["notification_id"]
        
        # Delete
        response = self.session.delete(f"{BASE_URL}/api/notifications/{notification_id}")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        result = response.json()
        assert "message" in result, "Missing message in response"
        
        # Verify deletion
        verify_response = self.session.get(
            f"{BASE_URL}/api/notifications/paginated",
            params={"page": 1, "page_size": 100}
        )
        verify_data = verify_response.json()
        deleted_ids = [n["notification_id"] for n in verify_data["notifications"]]
        assert notification_id not in deleted_ids, "Notification should be deleted"
        
        print(f"SUCCESS: Deleted notification {notification_id}")
    
    def test_delete_notification_not_found(self):
        """Test DELETE /api/notifications/{id} with invalid ID - returns 404"""
        fake_id = f"notif_{uuid.uuid4().hex[:12]}"
        
        response = self.session.delete(f"{BASE_URL}/api/notifications/{fake_id}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"SUCCESS: Got 404 for non-existent notification {fake_id}")
    
    # ==================== Basic Notifications List Tests ====================
    
    def test_get_notifications_list(self):
        """Test GET /api/notifications/ - returns notifications list"""
        response = self.session.get(f"{BASE_URL}/api/notifications/")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"SUCCESS: Got {len(data)} notifications from basic list endpoint")
    
    def test_get_notifications_list_with_limit(self):
        """Test GET /api/notifications/ with limit parameter"""
        response = self.session.get(
            f"{BASE_URL}/api/notifications/",
            params={"limit": 5}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) <= 5, "Should return at most 5 notifications"
        
        print(f"SUCCESS: Got {len(data)} notifications with limit=5")


class TestNotificationPreferencesAsTeamMember:
    """Test notification preferences as team member user"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with team member authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as team member
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=TEST_TEAM_MEMBER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        self.token = data.get("access_token")
        self.user_id = data.get("user", {}).get("user_id")
        
        assert self.token, "No token received"
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        self.session.close()
    
    def test_team_member_can_get_preferences(self):
        """Test team member can access their notification preferences"""
        response = self.session.get(f"{BASE_URL}/api/notifications/preferences")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["user_id"] == self.user_id, "Should return preferences for logged in user"
        
        print(f"SUCCESS: Team member {self.user_id} can access their preferences")
    
    def test_team_member_can_update_preferences(self):
        """Test team member can update their notification preferences"""
        update_payload = {
            "email_notifications_enabled": True,
            "quiet_hours_enabled": False
        }
        
        response = self.session.put(
            f"{BASE_URL}/api/notifications/preferences",
            json=update_payload
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        print(f"SUCCESS: Team member can update their preferences")


class TestNotificationAuthRequired:
    """Test that notification endpoints require authentication"""
    
    def test_preferences_requires_auth(self):
        """Test GET /api/notifications/preferences requires auth"""
        response = requests.get(f"{BASE_URL}/api/notifications/preferences")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Preferences endpoint requires authentication")
    
    def test_notifications_requires_auth(self):
        """Test GET /api/notifications/ requires auth"""
        response = requests.get(f"{BASE_URL}/api/notifications/")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Notifications endpoint requires authentication")
    
    def test_types_requires_auth(self):
        """Test GET /api/notifications/types requires auth"""
        response = requests.get(f"{BASE_URL}/api/notifications/types")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Types endpoint requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
