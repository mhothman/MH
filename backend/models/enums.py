"""Enumeration types for the application"""

class UserRole:
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    PROJECT_MANAGER = "project_manager"
    TEAM_MEMBER = "team_member"
    VIEWER = "viewer"
    
    @classmethod
    def all(cls):
        return [cls.SUPER_ADMIN, cls.ORG_ADMIN, cls.PROJECT_MANAGER, cls.TEAM_MEMBER, cls.VIEWER]
    
    @classmethod
    def admin_roles(cls):
        return [cls.SUPER_ADMIN, cls.ORG_ADMIN]

class ProjectStatus:
    PLANNED = "planned"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    
    @classmethod
    def all(cls):
        return [cls.PLANNED, cls.ACTIVE, cls.ON_HOLD, cls.COMPLETED, cls.ARCHIVED]

class TaskStatus:
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "review"
    DONE = "done"
    
    @classmethod
    def all(cls):
        return [cls.TODO, cls.IN_PROGRESS, cls.IN_REVIEW, cls.DONE]

class TaskPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    
    @classmethod
    def all(cls):
        return [cls.LOW, cls.MEDIUM, cls.HIGH, cls.URGENT]

class RecurrenceType:
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    
    @classmethod
    def all(cls):
        return [cls.DAILY, cls.WEEKLY, cls.MONTHLY]

class AuditAction:
    """Audit log action types"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    INVITE = "invite"
    REMOVE = "remove"
    SUSPEND = "suspend"
    UNSUSPEND = "unsuspend"
    CHANGE_ROLE = "change_role"
    RESET_PASSWORD = "reset_password"
    EXPORT = "export"
    # Approval workflow actions
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_EXPIRED = "approval_expired"
    APPROVAL_FORCE_APPROVED = "approval_force_approved"
    APPROVAL_FORCE_REJECTED = "approval_force_rejected"
    
    @classmethod
    def all(cls):
        return [
            cls.CREATE, cls.UPDATE, cls.DELETE, cls.LOGIN, cls.LOGOUT,
            cls.INVITE, cls.REMOVE, cls.SUSPEND, cls.UNSUSPEND,
            cls.CHANGE_ROLE, cls.RESET_PASSWORD, cls.EXPORT,
            cls.APPROVAL_REQUESTED, cls.APPROVAL_APPROVED, cls.APPROVAL_REJECTED,
            cls.APPROVAL_EXPIRED, cls.APPROVAL_FORCE_APPROVED, cls.APPROVAL_FORCE_REJECTED
        ]

class ResourceType:
    """Resource types for audit logging"""
    USER = "user"
    ORGANIZATION = "organization"
    PROJECT = "project"
    TASK = "task"
    COMMENT = "comment"
    CUSTOMER = "customer"
    MEMBER = "member"
    INVITATION = "invitation"
    SUBSCRIPTION = "subscription"
    AUTOMATION = "automation"
    WORKFLOW = "workflow"
    WORKFLOW_RULE = "workflow_rule"
    APPROVAL = "approval"
    
    @classmethod
    def all(cls):
        return [
            cls.USER, cls.ORGANIZATION, cls.PROJECT, cls.TASK,
            cls.COMMENT, cls.CUSTOMER, cls.MEMBER, cls.INVITATION,
            cls.SUBSCRIPTION, cls.AUTOMATION, cls.WORKFLOW, 
            cls.WORKFLOW_RULE, cls.APPROVAL
        ]


class ApprovalStatus:
    """Status of an approval request"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    
    @classmethod
    def all(cls):
        return [cls.PENDING, cls.APPROVED, cls.REJECTED, cls.EXPIRED]


class ApprovalType:
    """Type of approval required"""
    SINGLE = "single"  # Any one approver can approve
    MULTI = "multi"    # All approvers with the role must approve
    
    @classmethod
    def all(cls):
        return [cls.SINGLE, cls.MULTI]
