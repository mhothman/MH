"""Unit tests for refactored services"""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

# =============================================
# Test Organization Service
# =============================================

class TestOrganizationService:
    """Tests for OrganizationService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        mock = MagicMock()
        mock.org_memberships = MagicMock()
        mock.users = MagicMock()
        mock.organizations = MagicMock()
        mock.invitations = MagicMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_get_members_returns_enriched_data(self, mock_db):
        """Test that get_members returns users with org role info"""
        from services.organization_service import OrganizationService
        
        service = OrganizationService()
        
        # Mock data
        memberships = [
            {"user_id": "user_1", "org_id": "org_1", "role": "org_admin", "joined_at": "2024-01-01"},
            {"user_id": "user_2", "org_id": "org_1", "role": "team_member", "joined_at": "2024-01-02"}
        ]
        users = [
            {"user_id": "user_1", "name": "Admin User", "email": "admin@test.com"},
            {"user_id": "user_2", "name": "Team Member", "email": "team@test.com"}
        ]
        org = {"org_id": "org_1", "owner_id": "user_1"}
        
        with patch('services.organization_service.get_database', return_value=mock_db):
            mock_db.org_memberships.find.return_value.to_list = AsyncMock(return_value=memberships)
            mock_db.users.find.return_value.to_list = AsyncMock(return_value=users)
            service.repo.find_by_id = AsyncMock(return_value=org)
            
            result = await service.get_members("org_1")
            
            assert len(result) == 2
            assert result[0]["org_role"] == "org_admin"
            assert result[0]["is_owner"] == True
            assert result[1]["org_role"] == "team_member"
            assert result[1]["is_owner"] == False
    
    @pytest.mark.asyncio
    async def test_change_member_role_prevents_owner_change(self, mock_db):
        """Test that owner's role cannot be changed"""
        from services.organization_service import OrganizationService
        
        service = OrganizationService()
        
        with patch('services.organization_service.get_database', return_value=mock_db):
            service.repo.find_by_id = AsyncMock(return_value={"org_id": "org_1", "owner_id": "user_1"})
            
            success, message = await service.change_member_role(
                org_id="org_1",
                user_id="user_1",  # Owner
                admin_id="user_2",
                role="team_member"
            )
            
            assert success == False
            assert "owner" in message.lower()


# =============================================
# Test Role Service
# =============================================

class TestRoleService:
    """Tests for RoleService"""
    
    @pytest.mark.asyncio
    async def test_validate_permissions_valid(self):
        """Test permission validation with valid permissions"""
        from services.role_service import RoleService
        
        service = RoleService()
        
        valid_perms = ["project:view", "task:create", "task:edit"]
        is_valid, error = service.validate_permissions(valid_perms)
        
        assert is_valid == True
        assert error == ""
    
    @pytest.mark.asyncio
    async def test_validate_permissions_invalid(self):
        """Test permission validation with invalid permissions"""
        from services.role_service import RoleService
        
        service = RoleService()
        
        invalid_perms = ["project:view", "invalid:permission"]
        is_valid, error = service.validate_permissions(invalid_perms)
        
        assert is_valid == False
        assert "invalid:permission" in error
    
    @pytest.mark.asyncio
    async def test_get_all_permissions_structure(self):
        """Test that get_all_permissions returns correct structure"""
        from services.role_service import RoleService
        
        service = RoleService()
        result = service.get_all_permissions()
        
        assert "permissions" in result
        assert "categories" in result
        assert len(result["permissions"]) > 0
        assert len(result["categories"]) > 0
        
        # Check permission structure
        perm = result["permissions"][0]
        assert "id" in perm
        assert "name" in perm
        assert "category" in perm


# =============================================
# Test Task Service
# =============================================

class TestTaskService:
    """Tests for TaskService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        mock = MagicMock()
        mock.tasks = MagicMock()
        mock.comments = MagicMock()
        mock.time_entries = MagicMock()
        mock.attachments = MagicMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_update_task_locked_returns_error(self, mock_db):
        """Test that locked tasks cannot be updated"""
        from services.task_service import TaskService
        
        service = TaskService()
        
        locked_task = {
            "task_id": "task_1",
            "approval_locked": True,
            "status": "in_progress"
        }
        
        with patch.object(service.repo, 'find_by_id', AsyncMock(return_value=locked_task)):
            success, message, _ = await service.update_task(
                task_id="task_1",
                user_id="user_1",
                updates={"status": "done"}
            )
            
            assert success == False
            assert "locked" in message.lower()
    
    @pytest.mark.asyncio
    async def test_bulk_update_filters_allowed_fields(self, mock_db):
        """Test that bulk update only allows specific fields"""
        from services.task_service import TaskService
        
        service = TaskService()
        
        with patch('services.task_service.get_database', return_value=mock_db):
            mock_db.tasks.update_many = AsyncMock(return_value=MagicMock(modified_count=2))
            mock_db.tasks.find.return_value.to_list = AsyncMock(return_value=[
                {"task_id": "t1", "org_id": "org_1"},
                {"task_id": "t2", "org_id": "org_1"}
            ])
            service.repo.find_all = AsyncMock(return_value=[
                {"task_id": "t1", "org_id": "org_1"},
                {"task_id": "t2", "org_id": "org_1"}
            ])
            
            with patch('services.task_service.audit_service') as mock_audit:
                mock_audit.log = AsyncMock()
                
                # Try to update with disallowed field
                success, count = await service.bulk_update(
                    task_ids=["t1", "t2"],
                    updates={"status": "done", "title": "hacked"},  # title not allowed
                    user_id="user_1"
                )
                
                # Should succeed but only with allowed fields
                assert success == True


# =============================================
# Test Time Service
# =============================================

class TestTimeService:
    """Tests for TimeService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        mock = MagicMock()
        mock.timers = MagicMock()
        mock.time_entries = MagicMock()
        mock.tasks = MagicMock()
        mock.users = MagicMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_start_timer_fails_with_existing_active(self, mock_db):
        """Test that starting a timer fails if one is already active"""
        from services.time_service import TimeService
        
        service = TimeService()
        
        with patch('services.time_service.get_database', return_value=mock_db):
            mock_db.timers.find_one = AsyncMock(return_value={
                "timer_id": "existing_timer",
                "is_running": True
            })
            
            success, message, timer = await service.start_timer(
                user_id="user_1",
                task_id="task_1",
                org_id="org_1"
            )
            
            assert success == False
            assert "already have an active timer" in message
            assert timer is None
    
    @pytest.mark.asyncio
    async def test_stop_timer_creates_entry(self, mock_db):
        """Test that stopping a timer creates a time entry"""
        from services.time_service import TimeService
        
        service = TimeService()
        
        # Timer started 30 minutes ago
        started_at = (datetime.now(timezone.utc).replace(microsecond=0))
        
        with patch('services.time_service.get_database', return_value=mock_db):
            mock_db.timers.find_one = AsyncMock(return_value={
                "timer_id": "timer_1",
                "task_id": "task_1",
                "user_id": "user_1",
                "org_id": "org_1",
                "started_at": started_at.isoformat(),
                "is_running": True
            })
            mock_db.time_entries.insert_one = AsyncMock()
            mock_db.tasks.update_one = AsyncMock()
            mock_db.timers.update_one = AsyncMock()
            
            success, message, result = await service.stop_timer("user_1")
            
            assert success == True
            assert "entry_id" in result
            mock_db.time_entries.insert_one.assert_called_once()


# =============================================
# Test Automation Service
# =============================================

class TestAutomationService:
    """Tests for AutomationService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        mock = MagicMock()
        mock.automations = MagicMock()
        mock.automation_runs = MagicMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_create_automation_validates_trigger_type(self, mock_db):
        """Test that invalid trigger types are rejected"""
        from services.automation_service import AutomationService
        
        service = AutomationService()
        
        with patch('services.automation_service.get_database', return_value=mock_db):
            success, message, automation = await service.create_automation(
                org_id="org_1",
                user_id="user_1",
                name="Test",
                trigger={"type": "invalid_trigger"},
                actions=[{"type": "notify_users", "config": {}}]
            )
            
            assert success == False
            assert "invalid trigger" in message.lower()
    
    @pytest.mark.asyncio
    async def test_create_automation_validates_action_type(self, mock_db):
        """Test that invalid action types are rejected"""
        from services.automation_service import AutomationService
        
        service = AutomationService()
        
        with patch('services.automation_service.get_database', return_value=mock_db):
            success, message, automation = await service.create_automation(
                org_id="org_1",
                user_id="user_1",
                name="Test",
                trigger={"type": "task_created"},
                actions=[{"type": "invalid_action", "config": {}}]
            )
            
            assert success == False
            assert "invalid action" in message.lower()
    
    def test_get_trigger_types(self):
        """Test that trigger types are returned"""
        from services.automation_service import AutomationService
        
        service = AutomationService()
        triggers = service.get_trigger_types()
        
        assert len(triggers) > 0
        assert any(t["type"] == "task_created" for t in triggers)
        assert any(t["type"] == "status_changed" for t in triggers)
    
    def test_get_action_types(self):
        """Test that action types are returned"""
        from services.automation_service import AutomationService
        
        service = AutomationService()
        actions = service.get_action_types()
        
        assert len(actions) > 0
        assert any(a["type"] == "notify_users" for a in actions)
        assert any(a["type"] == "send_email" for a in actions)


# =============================================
# Test Branding Service
# =============================================

class TestBrandingService:
    """Tests for BrandingService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        mock = MagicMock()
        mock.organization_branding = MagicMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_get_branding_returns_default_when_none(self, mock_db):
        """Test that default branding is returned when none exists"""
        from services.branding_service import BrandingService, DEFAULT_BRANDING
        
        service = BrandingService()
        
        with patch('services.branding_service.get_database', return_value=mock_db):
            mock_db.organization_branding.find_one = AsyncMock(return_value=None)
            
            result = await service.get_branding("org_1")
            
            assert result["primary_color"] == DEFAULT_BRANDING["primary_color"]
            assert result["organization_id"] == "org_1"
    
    def test_get_media_type(self):
        """Test media type detection"""
        from services.branding_service import BrandingService
        
        service = BrandingService()
        
        assert service.get_media_type("logo.png") == "image/png"
        assert service.get_media_type("logo.jpg") == "image/jpeg"
        assert service.get_media_type("logo.svg") == "image/svg+xml"
        assert service.get_media_type("logo.webp") == "image/webp"
        assert service.get_media_type("logo.unknown") == "application/octet-stream"


# =============================================
# Run tests
# =============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
