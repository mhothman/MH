"""
Role-Based Access Control (RBAC) - Permissions definitions
Defines what each role can do across the application
"""

from typing import List, Dict

class Permission:
    """Permission identifiers"""
    # Project permissions
    PROJECT_VIEW = "project:view"
    PROJECT_CREATE = "project:create"
    PROJECT_EDIT = "project:edit"
    PROJECT_DELETE = "project:delete"
    PROJECT_ARCHIVE = "project:archive"
    PROJECT_MANAGE_TEAM = "project:manage_team"
    
    # Task permissions
    TASK_VIEW = "task:view"
    TASK_CREATE = "task:create"
    TASK_EDIT = "task:edit"
    TASK_EDIT_OWN = "task:edit_own"  # Edit only assigned tasks
    TASK_DELETE = "task:delete"
    TASK_ASSIGN = "task:assign"
    TASK_CHANGE_STATUS = "task:change_status"
    
    # Team/Member permissions
    MEMBER_VIEW = "member:view"
    MEMBER_INVITE = "member:invite"
    MEMBER_REMOVE = "member:remove"
    MEMBER_CHANGE_ROLE = "member:change_role"
    MEMBER_SUSPEND = "member:suspend"
    MEMBER_RESET_PASSWORD = "member:reset_password"
    
    # Customer permissions
    CUSTOMER_VIEW = "customer:view"
    CUSTOMER_CREATE = "customer:create"
    CUSTOMER_EDIT = "customer:edit"
    CUSTOMER_DELETE = "customer:delete"
    
    # Report permissions
    REPORT_VIEW = "report:view"
    REPORT_EXPORT = "report:export"
    REPORT_EXECUTIVE = "report:executive"
    
    # Settings permissions
    SETTINGS_VIEW = "settings:view"
    SETTINGS_EDIT = "settings:edit"
    SETTINGS_BILLING = "settings:billing"
    
    # Automation permissions
    AUTOMATION_VIEW = "automation:view"
    AUTOMATION_CREATE = "automation:create"
    AUTOMATION_EDIT = "automation:edit"
    AUTOMATION_DELETE = "automation:delete"
    
    # Audit permissions
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"
    
    # Comment permissions
    COMMENT_VIEW = "comment:view"
    COMMENT_CREATE = "comment:create"
    COMMENT_EDIT_OWN = "comment:edit_own"
    COMMENT_DELETE_ANY = "comment:delete_any"
    
    # Time tracking permissions
    TIME_VIEW_OWN = "time:view_own"
    TIME_VIEW_ALL = "time:view_all"
    TIME_CREATE = "time:create"
    TIME_EDIT_OWN = "time:edit_own"
    
    # Workflow permissions
    WORKFLOW_VIEW = "workflow:view"
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_EDIT = "workflow:edit"
    WORKFLOW_DELETE = "workflow:delete"
    WORKFLOW_ASSIGN = "workflow:assign"  # Assign workflow to project
    
    # Approval permissions
    APPROVAL_VIEW = "approval:view"
    APPROVAL_REQUEST = "approval:request"
    APPROVAL_APPROVE = "approval:approve"
    APPROVAL_REJECT = "approval:reject"
    APPROVAL_FORCE = "approval:force"  # Force approve/reject (admin override)
    
    # Document permissions
    DOCUMENT_VIEW = "document:view"
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_EDIT = "document:edit"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_CHANGE_STATUS = "document:change_status"
    DOCUMENT_APPROVE = "document:approve"
    
    # Budget permissions
    BUDGET_VIEW = "budget:view"
    BUDGET_CREATE = "budget:create"
    BUDGET_EDIT = "budget:edit"
    BUDGET_DELETE = "budget:delete"
    BUDGET_APPROVE = "budget:approve"  # Approve budget changes
    BUDGET_OVERRIDE = "budget:override"  # Override hard limit
    
    # Expense permissions
    EXPENSE_VIEW = "expense:view"
    EXPENSE_CREATE = "expense:create"
    EXPENSE_EDIT = "expense:edit"
    EXPENSE_DELETE = "expense:delete"
    EXPENSE_APPROVE = "expense:approve"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "super_admin": [
        # Super admin has ALL permissions
        Permission.PROJECT_VIEW, Permission.PROJECT_CREATE, Permission.PROJECT_EDIT, 
        Permission.PROJECT_DELETE, Permission.PROJECT_ARCHIVE, Permission.PROJECT_MANAGE_TEAM,
        Permission.TASK_VIEW, Permission.TASK_CREATE, Permission.TASK_EDIT, Permission.TASK_DELETE,
        Permission.TASK_ASSIGN, Permission.TASK_CHANGE_STATUS,
        Permission.MEMBER_VIEW, Permission.MEMBER_INVITE, Permission.MEMBER_REMOVE,
        Permission.MEMBER_CHANGE_ROLE, Permission.MEMBER_SUSPEND, Permission.MEMBER_RESET_PASSWORD,
        Permission.CUSTOMER_VIEW, Permission.CUSTOMER_CREATE, Permission.CUSTOMER_EDIT, Permission.CUSTOMER_DELETE,
        Permission.REPORT_VIEW, Permission.REPORT_EXPORT, Permission.REPORT_EXECUTIVE,
        Permission.SETTINGS_VIEW, Permission.SETTINGS_EDIT, Permission.SETTINGS_BILLING,
        Permission.AUTOMATION_VIEW, Permission.AUTOMATION_CREATE, Permission.AUTOMATION_EDIT, Permission.AUTOMATION_DELETE,
        Permission.AUDIT_VIEW, Permission.AUDIT_EXPORT,
        Permission.COMMENT_VIEW, Permission.COMMENT_CREATE, Permission.COMMENT_EDIT_OWN, Permission.COMMENT_DELETE_ANY,
        Permission.TIME_VIEW_OWN, Permission.TIME_VIEW_ALL, Permission.TIME_CREATE, Permission.TIME_EDIT_OWN,
        # Workflow permissions
        Permission.WORKFLOW_VIEW, Permission.WORKFLOW_CREATE, Permission.WORKFLOW_EDIT, 
        Permission.WORKFLOW_DELETE, Permission.WORKFLOW_ASSIGN,
        Permission.APPROVAL_VIEW, Permission.APPROVAL_REQUEST, Permission.APPROVAL_APPROVE,
        Permission.APPROVAL_REJECT, Permission.APPROVAL_FORCE,
        # Document permissions
        Permission.DOCUMENT_VIEW, Permission.DOCUMENT_CREATE, Permission.DOCUMENT_EDIT,
        Permission.DOCUMENT_DELETE, Permission.DOCUMENT_CHANGE_STATUS, Permission.DOCUMENT_APPROVE,
        # Budget permissions
        Permission.BUDGET_VIEW, Permission.BUDGET_CREATE, Permission.BUDGET_EDIT,
        Permission.BUDGET_DELETE, Permission.BUDGET_APPROVE, Permission.BUDGET_OVERRIDE,
        # Expense permissions
        Permission.EXPENSE_VIEW, Permission.EXPENSE_CREATE, Permission.EXPENSE_EDIT,
        Permission.EXPENSE_DELETE, Permission.EXPENSE_APPROVE,
    ],
    
    "org_admin": [
        # Org admin has most permissions except system-level ones
        Permission.PROJECT_VIEW, Permission.PROJECT_CREATE, Permission.PROJECT_EDIT, 
        Permission.PROJECT_DELETE, Permission.PROJECT_ARCHIVE, Permission.PROJECT_MANAGE_TEAM,
        Permission.TASK_VIEW, Permission.TASK_CREATE, Permission.TASK_EDIT, Permission.TASK_DELETE,
        Permission.TASK_ASSIGN, Permission.TASK_CHANGE_STATUS,
        Permission.MEMBER_VIEW, Permission.MEMBER_INVITE, Permission.MEMBER_REMOVE,
        Permission.MEMBER_CHANGE_ROLE, Permission.MEMBER_SUSPEND, Permission.MEMBER_RESET_PASSWORD,
        Permission.CUSTOMER_VIEW, Permission.CUSTOMER_CREATE, Permission.CUSTOMER_EDIT, Permission.CUSTOMER_DELETE,
        Permission.REPORT_VIEW, Permission.REPORT_EXPORT, Permission.REPORT_EXECUTIVE,
        Permission.SETTINGS_VIEW, Permission.SETTINGS_EDIT,
        Permission.AUTOMATION_VIEW, Permission.AUTOMATION_CREATE, Permission.AUTOMATION_EDIT, Permission.AUTOMATION_DELETE,
        Permission.AUDIT_VIEW, Permission.AUDIT_EXPORT,
        Permission.COMMENT_VIEW, Permission.COMMENT_CREATE, Permission.COMMENT_EDIT_OWN, Permission.COMMENT_DELETE_ANY,
        Permission.TIME_VIEW_OWN, Permission.TIME_VIEW_ALL, Permission.TIME_CREATE, Permission.TIME_EDIT_OWN,
        # Workflow permissions - Org Admin can define and manage workflows
        Permission.WORKFLOW_VIEW, Permission.WORKFLOW_CREATE, Permission.WORKFLOW_EDIT, 
        Permission.WORKFLOW_DELETE, Permission.WORKFLOW_ASSIGN,
        Permission.APPROVAL_VIEW, Permission.APPROVAL_REQUEST, Permission.APPROVAL_APPROVE,
        Permission.APPROVAL_REJECT, Permission.APPROVAL_FORCE,
        # Document permissions
        Permission.DOCUMENT_VIEW, Permission.DOCUMENT_CREATE, Permission.DOCUMENT_EDIT,
        Permission.DOCUMENT_DELETE, Permission.DOCUMENT_CHANGE_STATUS, Permission.DOCUMENT_APPROVE,
        # Budget permissions - Org Admin can manage budgets
        Permission.BUDGET_VIEW, Permission.BUDGET_CREATE, Permission.BUDGET_EDIT,
        Permission.BUDGET_DELETE, Permission.BUDGET_APPROVE,
        # Expense permissions
        Permission.EXPENSE_VIEW, Permission.EXPENSE_CREATE, Permission.EXPENSE_EDIT,
        Permission.EXPENSE_DELETE, Permission.EXPENSE_APPROVE,
    ],
    
    "project_manager": [
        # Project manager can manage projects and tasks, view team
        Permission.PROJECT_VIEW, Permission.PROJECT_CREATE, Permission.PROJECT_EDIT, Permission.PROJECT_MANAGE_TEAM,
        Permission.TASK_VIEW, Permission.TASK_CREATE, Permission.TASK_EDIT, Permission.TASK_DELETE,
        Permission.TASK_ASSIGN, Permission.TASK_CHANGE_STATUS,
        Permission.MEMBER_VIEW,
        Permission.CUSTOMER_VIEW, Permission.CUSTOMER_CREATE, Permission.CUSTOMER_EDIT,
        Permission.REPORT_VIEW, Permission.REPORT_EXPORT,
        Permission.SETTINGS_VIEW,
        Permission.AUTOMATION_VIEW, Permission.AUTOMATION_CREATE, Permission.AUTOMATION_EDIT,
        Permission.AUDIT_VIEW,
        Permission.COMMENT_VIEW, Permission.COMMENT_CREATE, Permission.COMMENT_EDIT_OWN,
        Permission.TIME_VIEW_OWN, Permission.TIME_VIEW_ALL, Permission.TIME_CREATE, Permission.TIME_EDIT_OWN,
        # Workflow permissions - PM can assign workflows and approve
        Permission.WORKFLOW_VIEW, Permission.WORKFLOW_ASSIGN,
        Permission.APPROVAL_VIEW, Permission.APPROVAL_REQUEST, Permission.APPROVAL_APPROVE,
        Permission.APPROVAL_REJECT,
        # Document permissions - PM can create, edit, and approve
        Permission.DOCUMENT_VIEW, Permission.DOCUMENT_CREATE, Permission.DOCUMENT_EDIT,
        Permission.DOCUMENT_CHANGE_STATUS, Permission.DOCUMENT_APPROVE,
        # Budget permissions - PM can view and request changes
        Permission.BUDGET_VIEW,
        # Expense permissions - PM can manage expenses
        Permission.EXPENSE_VIEW, Permission.EXPENSE_CREATE, Permission.EXPENSE_EDIT,
        Permission.EXPENSE_DELETE,
    ],
    
    "team_member": [
        # Team member can work on tasks, limited editing
        Permission.PROJECT_VIEW,
        Permission.TASK_VIEW, Permission.TASK_CREATE, Permission.TASK_EDIT_OWN, Permission.TASK_CHANGE_STATUS,
        Permission.MEMBER_VIEW,
        Permission.CUSTOMER_VIEW,
        Permission.REPORT_VIEW,
        Permission.SETTINGS_VIEW,
        Permission.COMMENT_VIEW, Permission.COMMENT_CREATE, Permission.COMMENT_EDIT_OWN,
        Permission.TIME_VIEW_OWN, Permission.TIME_CREATE, Permission.TIME_EDIT_OWN,
        # Workflow permissions - Team member can view and request approvals
        Permission.WORKFLOW_VIEW,
        Permission.APPROVAL_VIEW, Permission.APPROVAL_REQUEST,
        # Document permissions - Team member can view and create
        Permission.DOCUMENT_VIEW, Permission.DOCUMENT_CREATE, Permission.DOCUMENT_EDIT,
        Permission.DOCUMENT_CHANGE_STATUS,
        # Budget permissions - Team member can view
        Permission.BUDGET_VIEW,
        # Expense permissions - Team member can view and create
        Permission.EXPENSE_VIEW, Permission.EXPENSE_CREATE,
    ],
    
    "viewer": [
        # Viewer has read-only access
        Permission.PROJECT_VIEW,
        Permission.TASK_VIEW,
        Permission.MEMBER_VIEW,
        Permission.CUSTOMER_VIEW,
        Permission.REPORT_VIEW,
        Permission.COMMENT_VIEW,
        Permission.TIME_VIEW_OWN,
        # Workflow permissions - Viewer can only view
        Permission.WORKFLOW_VIEW,
        Permission.APPROVAL_VIEW,
        # Document permissions - Viewer can only view
        Permission.DOCUMENT_VIEW,
        # Budget permissions - Viewer can only view
        Permission.BUDGET_VIEW,
        Permission.EXPENSE_VIEW,
    ],
}


def get_role_permissions(role: str) -> List[str]:
    """Get all permissions for a role"""
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission"""
    return permission in get_role_permissions(role)


def has_any_permission(role: str, permissions: List[str]) -> bool:
    """Check if a role has any of the specified permissions"""
    role_perms = get_role_permissions(role)
    return any(p in role_perms for p in permissions)


def has_all_permissions(role: str, permissions: List[str]) -> bool:
    """Check if a role has all of the specified permissions"""
    role_perms = get_role_permissions(role)
    return all(p in role_perms for p in permissions)


# Role hierarchy for comparing roles
ROLE_HIERARCHY = {
    "super_admin": 5,
    "org_admin": 4,
    "project_manager": 3,
    "team_member": 2,
    "viewer": 1,
}


def is_role_higher_or_equal(role1: str, role2: str) -> bool:
    """Check if role1 is higher or equal to role2 in hierarchy"""
    return ROLE_HIERARCHY.get(role1, 0) >= ROLE_HIERARCHY.get(role2, 0)


def can_manage_role(manager_role: str, target_role: str) -> bool:
    """Check if a manager can manage users with target role"""
    # Must be strictly higher to manage
    return ROLE_HIERARCHY.get(manager_role, 0) > ROLE_HIERARCHY.get(target_role, 0)
