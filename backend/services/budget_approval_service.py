"""Budget Approval Service - Handles approval workflow for budget changes"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from uuid import uuid4

from core.database import get_database
from services.notification_service import notification_service
from services.audit_service import audit_service

logger = logging.getLogger(__name__)


class BudgetApprovalService:
    """Service for managing budget change approvals"""
    
    async def create_approval_request(
        self,
        budget_id: str,
        change_type: str,
        current_value: float,
        proposed_value: float,
        reason: Optional[str],
        requested_by: str,
        org_id: str
    ) -> Dict:
        """Create a new budget approval request"""
        db = get_database()
        
        # Get budget and project info
        budget = await db.project_budgets.find_one({"budget_id": budget_id}, {"_id": 0})
        if not budget:
            raise ValueError("Budget not found")
        
        project = await db.projects.find_one(
            {"project_id": budget["project_id"]}, 
            {"_id": 0, "name": 1}
        )
        project_name = project["name"] if project else "Unknown"
        
        # Get requester name
        requester = await db.users.find_one(
            {"user_id": requested_by}, 
            {"_id": 0, "name": 1}
        )
        requester_name = requester["name"] if requester else "Unknown"
        
        approval_id = f"bappr_{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        approval = {
            "approval_id": approval_id,
            "budget_id": budget_id,
            "project_id": budget["project_id"],
            "project_name": project_name,
            "org_id": org_id,
            "change_type": change_type,
            "current_value": current_value,
            "proposed_value": proposed_value,
            "reason": reason,
            "status": "pending",
            "requested_by": requested_by,
            "requester_name": requester_name,
            "created_at": now,
            "reviewed_by": None,
            "reviewer_name": None,
            "reviewed_at": None,
            "review_notes": None
        }
        
        await db.budget_approvals.insert_one(approval)
        approval.pop("_id", None)
        
        # Send notifications to Finance role users
        await self._notify_finance_users(org_id, approval)
        
        # Log audit
        await audit_service.log(
            org_id=org_id,
            user_id=requested_by,
            action="budget_approval.request",
            resource_type="budget",
            resource_id=budget_id,
            details={
                "approval_id": approval_id,
                "change_type": change_type,
                "current_value": current_value,
                "proposed_value": proposed_value
            }
        )
        
        logger.info(f"Budget approval request created: {approval_id} for budget {budget_id}")
        return approval
    
    async def approve_request(
        self,
        approval_id: str,
        reviewed_by: str,
        notes: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Approve a budget change request"""
        db = get_database()
        
        approval = await db.budget_approvals.find_one(
            {"approval_id": approval_id}, 
            {"_id": 0}
        )
        if not approval:
            return False, "Approval request not found", None
        
        if approval["status"] != "pending":
            return False, f"Request is already {approval['status']}", None
        
        # Get reviewer name
        reviewer = await db.users.find_one(
            {"user_id": reviewed_by}, 
            {"_id": 0, "name": 1}
        )
        reviewer_name = reviewer["name"] if reviewer else "Unknown"
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Update approval status
        await db.budget_approvals.update_one(
            {"approval_id": approval_id},
            {"$set": {
                "status": "approved",
                "reviewed_by": reviewed_by,
                "reviewer_name": reviewer_name,
                "reviewed_at": now,
                "review_notes": notes
            }}
        )
        
        # Apply the budget change based on change_type
        await self._apply_budget_change(approval)
        
        # Notify requester
        await notification_service.create_notification(
            user_id=approval["requested_by"],
            title="Budget Change Approved",
            message=f"Your budget change request for {approval['project_name']} has been approved by {reviewer_name}.",
            type="budget_change",
            data={"approval_id": approval_id, "budget_id": approval["budget_id"]}
        )
        
        # Log audit
        await audit_service.log(
            org_id=approval["org_id"],
            user_id=reviewed_by,
            action="budget_approval.approve",
            resource_type="budget",
            resource_id=approval["budget_id"],
            details={
                "approval_id": approval_id,
                "change_type": approval["change_type"],
                "notes": notes
            }
        )
        
        logger.info(f"Budget approval {approval_id} approved by {reviewed_by}")
        approval["status"] = "approved"
        approval["reviewed_by"] = reviewed_by
        approval["reviewer_name"] = reviewer_name
        approval["reviewed_at"] = now
        approval["review_notes"] = notes
        
        return True, "Budget change approved successfully", approval
    
    async def reject_request(
        self,
        approval_id: str,
        reviewed_by: str,
        notes: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Reject a budget change request"""
        db = get_database()
        
        approval = await db.budget_approvals.find_one(
            {"approval_id": approval_id}, 
            {"_id": 0}
        )
        if not approval:
            return False, "Approval request not found", None
        
        if approval["status"] != "pending":
            return False, f"Request is already {approval['status']}", None
        
        # Get reviewer name
        reviewer = await db.users.find_one(
            {"user_id": reviewed_by}, 
            {"_id": 0, "name": 1}
        )
        reviewer_name = reviewer["name"] if reviewer else "Unknown"
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Update approval status
        await db.budget_approvals.update_one(
            {"approval_id": approval_id},
            {"$set": {
                "status": "rejected",
                "reviewed_by": reviewed_by,
                "reviewer_name": reviewer_name,
                "reviewed_at": now,
                "review_notes": notes
            }}
        )
        
        # Notify requester
        await notification_service.create_notification(
            user_id=approval["requested_by"],
            title="Budget Change Rejected",
            message=f"Your budget change request for {approval['project_name']} has been rejected by {reviewer_name}. Reason: {notes or 'No reason provided'}",
            type="budget_change",
            data={"approval_id": approval_id, "budget_id": approval["budget_id"]}
        )
        
        # Log audit
        await audit_service.log(
            org_id=approval["org_id"],
            user_id=reviewed_by,
            action="budget_approval.reject",
            resource_type="budget",
            resource_id=approval["budget_id"],
            details={
                "approval_id": approval_id,
                "change_type": approval["change_type"],
                "notes": notes
            }
        )
        
        logger.info(f"Budget approval {approval_id} rejected by {reviewed_by}")
        approval["status"] = "rejected"
        approval["reviewed_by"] = reviewed_by
        approval["reviewer_name"] = reviewer_name
        approval["reviewed_at"] = now
        approval["review_notes"] = notes
        
        return True, "Budget change rejected", approval
    
    async def get_pending_approvals(self, org_id: str) -> List[Dict]:
        """Get all pending budget approval requests for an organization"""
        db = get_database()
        
        approvals = await db.budget_approvals.find(
            {"org_id": org_id, "status": "pending"},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        
        return approvals
    
    async def get_approval(self, approval_id: str) -> Optional[Dict]:
        """Get a specific approval request"""
        db = get_database()
        return await db.budget_approvals.find_one(
            {"approval_id": approval_id}, 
            {"_id": 0}
        )
    
    async def get_budget_approvals(self, budget_id: str) -> List[Dict]:
        """Get all approval requests for a specific budget"""
        db = get_database()
        
        approvals = await db.budget_approvals.find(
            {"budget_id": budget_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        
        return approvals
    
    async def _apply_budget_change(self, approval: Dict) -> None:
        """Apply the approved budget change"""
        db = get_database()
        
        budget_id = approval["budget_id"]
        change_type = approval["change_type"]
        new_value = approval["proposed_value"]
        
        updates = {}
        
        if change_type in ["amount_increase", "amount_decrease"]:
            updates["total_budget"] = new_value
        elif change_type == "threshold_change":
            updates["warning_threshold_percent"] = new_value
        elif change_type == "hard_limit_change":
            updates["hard_limit"] = bool(new_value)
        
        if updates:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            await db.project_budgets.update_one(
                {"budget_id": budget_id},
                {"$set": updates}
            )
            
            # Recalculate budget if amount changed
            if "total_budget" in updates:
                from services.budget_service import budget_service
                await budget_service.recalculate_budget(budget_id)
    
    async def _notify_finance_users(self, org_id: str, approval: Dict) -> None:
        """Send notifications to all Finance role users in the organization"""
        db = get_database()
        
        # Get all org members with Finance role
        finance_members = await db.org_members.find(
            {"org_id": org_id, "role": "finance"},
            {"_id": 0, "user_id": 1}
        ).to_list(100)
        
        # Send notification to each finance user
        for member in finance_members:
            try:
                await notification_service.create_notification(
                    user_id=member["user_id"],
                    title="Budget Approval Required",
                    message=f"A budget change request for {approval['project_name']} requires your approval.",
                    type="budget_approval",
                    data={
                        "approval_id": approval["approval_id"],
                        "budget_id": approval["budget_id"],
                        "change_type": approval["change_type"]
                    }
                )
            except Exception as e:
                logger.error(f"Failed to notify finance user {member['user_id']}: {e}")


# Singleton instance
budget_approval_service = BudgetApprovalService()
