"""Budget Service for Project Budget Management"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import logging

from core.database import get_database
from services.notification_service import notification_service
from services.audit_service import audit_service

logger = logging.getLogger(__name__)


class BudgetService:
    """Service for managing project budgets, expenses, and transactions"""
    
    # ==================== Budget Operations ====================
    
    async def create_budget(
        self,
        org_id: str,
        project_id: str,
        total_budget: float,
        currency: str,
        warning_threshold_percent: float,
        hard_limit: bool,
        notes: Optional[str],
        created_by: str
    ) -> Dict:
        """Create a new project budget"""
        db = get_database()
        
        # Check if project already has a budget
        existing = await db.project_budgets.find_one({
            "project_id": project_id,
            "org_id": org_id
        }, {"_id": 0})
        
        if existing:
            raise ValueError("Project already has a budget. Update the existing budget instead.")
        
        # Verify project exists
        project = await db.projects.find_one({"project_id": project_id}, {"_id": 0, "name": 1})
        if not project:
            raise ValueError("Project not found")
        
        budget_id = f"budget_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        budget = {
            "budget_id": budget_id,
            "org_id": org_id,
            "project_id": project_id,
            "total_budget": total_budget,
            "currency": currency,
            "warning_threshold_percent": warning_threshold_percent,
            "hard_limit": hard_limit,
            "status": "active",
            "spent_amount": 0.0,
            "remaining_amount": total_budget,
            "spent_percent": 0.0,
            "notes": notes,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
        }
        
        await db.project_budgets.insert_one(budget)
        
        # Log audit
        await audit_service.log(
            org_id=org_id,
            user_id=created_by,
            action="budget.create",
            resource_type="budget",
            resource_id=budget_id,
            details={
                "project_id": project_id,
                "total_budget": total_budget,
                "currency": currency
            }
        )
        
        budget.pop("_id", None)
        return budget
    
    async def get_budget(self, budget_id: str) -> Optional[Dict]:
        """Get budget by ID"""
        db = get_database()
        budget = await db.project_budgets.find_one({"budget_id": budget_id}, {"_id": 0})
        return budget
    
    async def get_budget_by_project(self, project_id: str) -> Optional[Dict]:
        """Get budget for a specific project"""
        db = get_database()
        budget = await db.project_budgets.find_one({"project_id": project_id}, {"_id": 0})
        return budget
    
    async def get_budgets_by_org(self, org_id: str) -> List[Dict]:
        """Get all budgets for an organization"""
        db = get_database()
        budgets = await db.project_budgets.find(
            {"org_id": org_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(1000)
        
        # Fetch project names
        project_ids = [b["project_id"] for b in budgets if b.get("project_id")]
        logger.info(f"Fetching project names for {len(project_ids)} projects: {project_ids}")
        if project_ids:
            projects = await db.projects.find(
                {"project_id": {"$in": project_ids}},
                {"_id": 0, "project_id": 1, "name": 1}
            ).to_list(len(project_ids))
            logger.info(f"Found {len(projects)} projects: {projects}")
            projects_map = {p["project_id"]: p["name"] for p in projects}
            
            for budget in budgets:
                budget["project_name"] = projects_map.get(budget["project_id"], "Unknown")
                logger.info(f"Budget {budget['budget_id']} assigned project_name: {budget.get('project_name')}")
        
        logger.info(f"Returning {len(budgets)} budgets with project names")
        return budgets
    
    async def update_budget(
        self,
        budget_id: str,
        updates: Dict,
        updated_by: str,
        reason: Optional[str] = None
    ) -> Dict:
        """Update a project budget"""
        db = get_database()
        
        budget = await self.get_budget(budget_id)
        if not budget:
            raise ValueError("Budget not found")
        
        # Track budget amount changes for revision history
        if "total_budget" in updates and updates["total_budget"] != budget["total_budget"]:
            await self._create_revision(
                budget_id=budget_id,
                previous_budget=budget["total_budget"],
                new_budget=updates["total_budget"],
                reason=reason,
                created_by=updated_by
            )
        
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.project_budgets.update_one(
            {"budget_id": budget_id},
            {"$set": updates}
        )
        
        # Recalculate budget status
        await self.recalculate_budget(budget_id)
        
        # Log audit
        await audit_service.log(
            org_id=budget["org_id"],
            user_id=updated_by,
            action="budget.update",
            resource_type="budget",
            resource_id=budget_id,
            details=updates
        )
        
        return await self.get_budget(budget_id)
    
    async def delete_budget(self, budget_id: str, deleted_by: str) -> bool:
        """Delete a project budget"""
        db = get_database()
        
        budget = await self.get_budget(budget_id)
        if not budget:
            raise ValueError("Budget not found")
        
        # Delete related transactions
        await db.budget_transactions.delete_many({"budget_id": budget_id})
        
        # Delete related revisions
        await db.budget_revisions.delete_many({"budget_id": budget_id})
        
        # Delete budget
        await db.project_budgets.delete_one({"budget_id": budget_id})
        
        # Log audit
        await audit_service.log(
            org_id=budget["org_id"],
            user_id=deleted_by,
            action="budget.delete",
            resource_type="budget",
            resource_id=budget_id,
            details={"project_id": budget["project_id"]}
        )
        
        return True
    
    # ==================== Transaction Operations ====================
    
    async def create_transaction(
        self,
        budget_id: str,
        source: str,
        amount: float,
        created_by: str,
        reference_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict:
        """Create a budget transaction"""
        db = get_database()
        
        budget = await self.get_budget(budget_id)
        if not budget:
            raise ValueError("Budget not found")
        
        # Check hard limit
        if budget["hard_limit"] and budget["status"] == "locked":
            raise ValueError("Budget is locked. Cannot add new transactions.")
        
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        transaction = {
            "transaction_id": transaction_id,
            "budget_id": budget_id,
            "source": source,
            "reference_id": reference_id,
            "amount": amount,
            "description": description,
            "created_at": now,
            "created_by": created_by,
        }
        
        await db.budget_transactions.insert_one(transaction)
        
        # Recalculate budget
        await self.recalculate_budget(budget_id)
        
        transaction.pop("_id", None)
        return transaction
    
    async def get_transactions(
        self,
        budget_id: str,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get transactions for a budget"""
        db = get_database()
        
        query = {"budget_id": budget_id}
        if source:
            query["source"] = source
        
        transactions = await db.budget_transactions.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).skip(offset).limit(limit).to_list(limit)
        
        # Get user names
        user_ids = list(set([t["created_by"] for t in transactions]))
        users_map = {}
        if user_ids:
            users = await db.users.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1}
            ).to_list(len(user_ids))
            users_map = {u["user_id"]: u["name"] for u in users}
        
        for txn in transactions:
            txn["created_by_name"] = users_map.get(txn["created_by"])
        
        return transactions
    
    async def delete_transaction(self, transaction_id: str, deleted_by: str) -> bool:
        """Delete a budget transaction"""
        db = get_database()
        
        transaction = await db.budget_transactions.find_one(
            {"transaction_id": transaction_id},
            {"_id": 0}
        )
        
        if not transaction:
            raise ValueError("Transaction not found")
        
        await db.budget_transactions.delete_one({"transaction_id": transaction_id})
        
        # Recalculate budget
        await self.recalculate_budget(transaction["budget_id"])
        
        return True
    
    # ==================== Budget Calculations ====================
    
    async def recalculate_budget(self, budget_id: str) -> Dict:
        """Recalculate budget spent amount and status"""
        db = get_database()
        
        budget = await self.get_budget(budget_id)
        if not budget:
            raise ValueError("Budget not found")
        
        # Get the old spent_percent before recalculation
        old_spent_percent = budget.get("spent_percent", 0)
        
        # Sum all transactions
        pipeline = [
            {"$match": {"budget_id": budget_id}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        
        result = await db.budget_transactions.aggregate(pipeline).to_list(1)
        spent_amount = result[0]["total"] if result else 0.0
        
        # Calculate remaining and percentage
        remaining_amount = budget["total_budget"] - spent_amount
        spent_percent = (spent_amount / budget["total_budget"]) * 100 if budget["total_budget"] > 0 else 0
        
        # Determine status
        old_status = budget["status"]
        new_status = "active"
        
        if spent_percent >= 100:
            new_status = "locked" if budget["hard_limit"] else "exceeded"
        elif spent_percent >= budget["warning_threshold_percent"]:
            new_status = "warning"
        
        # Update budget
        await db.project_budgets.update_one(
            {"budget_id": budget_id},
            {"$set": {
                "spent_amount": round(spent_amount, 2),
                "remaining_amount": round(remaining_amount, 2),
                "spent_percent": round(spent_percent, 2),
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Send notifications on status change
        if old_status != new_status:
            await self._send_budget_notification(budget_id, old_status, new_status)
        
        # Send 50% threshold notification (only once, when crossing from below 50% to above 50%)
        if old_spent_percent < 50 and spent_percent >= 50:
            await self._send_fifty_percent_notification(budget_id, spent_percent)
        
        return await self.get_budget(budget_id)
    
    async def get_budget_summary(self, budget_id: str) -> Dict:
        """Get comprehensive budget summary with breakdown"""
        db = get_database()
        
        budget = await self.get_budget(budget_id)
        if not budget:
            raise ValueError("Budget not found")
        
        # Get project name
        project = await db.projects.find_one(
            {"project_id": budget["project_id"]},
            {"_id": 0, "name": 1}
        )
        
        # Get spend breakdown by source
        pipeline = [
            {"$match": {"budget_id": budget_id}},
            {"$group": {"_id": "$source", "total": {"$sum": "$amount"}}}
        ]
        
        breakdown = await db.budget_transactions.aggregate(pipeline).to_list(10)
        breakdown_map = {item["_id"]: item["total"] for item in breakdown}
        
        time_cost = breakdown_map.get("time_entry", 0.0)
        expense_cost = breakdown_map.get("expense", 0.0)
        manual_adjustments = breakdown_map.get("manual", 0.0) + breakdown_map.get("adjustment", 0.0)
        
        # Calculate burn rate (average daily spend over last 30 days)
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        recent_pipeline = [
            {"$match": {
                "budget_id": budget_id,
                "created_at": {"$gte": thirty_days_ago},
                "amount": {"$gt": 0}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        
        recent_result = await db.budget_transactions.aggregate(recent_pipeline).to_list(1)
        recent_spend = recent_result[0]["total"] if recent_result else 0
        burn_rate_daily = round(recent_spend / 30, 2) if recent_spend > 0 else None
        
        # Project end date at current burn rate
        projected_end_date = None
        days_remaining = None
        if burn_rate_daily and burn_rate_daily > 0 and budget["remaining_amount"] > 0:
            days_remaining = int(budget["remaining_amount"] / burn_rate_daily)
            projected_end_date = (datetime.now(timezone.utc) + timedelta(days=days_remaining)).strftime("%Y-%m-%d")
        
        return {
            "budget_id": budget_id,
            "project_id": budget["project_id"],
            "project_name": project["name"] if project else "Unknown",
            "total_budget": budget["total_budget"],
            "currency": budget["currency"],
            "status": budget["status"],
            "warning_threshold_percent": budget["warning_threshold_percent"],
            "hard_limit": budget["hard_limit"],
            "total_spent": budget["spent_amount"],
            "time_cost": round(time_cost, 2),
            "expense_cost": round(expense_cost, 2),
            "manual_adjustments": round(manual_adjustments, 2),
            "remaining": budget["remaining_amount"],
            "spent_percent": budget["spent_percent"],
            "burn_rate_daily": burn_rate_daily,
            "projected_end_date": projected_end_date,
            "days_remaining": days_remaining,
            "is_warning": budget["status"] == "warning",
            "is_exceeded": budget["status"] == "exceeded",
            "is_locked": budget["status"] == "locked",
        }
    
    # ==================== Expense Operations ====================
    
    async def create_expense(
        self,
        org_id: str,
        project_id: str,
        title: str,
        amount: float,
        currency: str,
        category: str,
        date: str,
        created_by: str,
        description: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> Dict:
        """Create a new expense entry"""
        db = get_database()
        
        # Verify project exists
        project = await db.projects.find_one({"project_id": project_id}, {"_id": 0})
        if not project:
            raise ValueError("Project not found")
        
        expense_id = f"exp_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        expense = {
            "expense_id": expense_id,
            "org_id": org_id,
            "project_id": project_id,
            "title": title,
            "amount": amount,
            "currency": currency,
            "category": category,
            "date": date,
            "description": description,
            "document_id": document_id,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
        }
        
        await db.expenses.insert_one(expense)
        
        # Add to budget transactions if project has a budget
        budget = await self.get_budget_by_project(project_id)
        if budget:
            await self.create_transaction(
                budget_id=budget["budget_id"],
                source="expense",
                amount=amount,
                created_by=created_by,
                reference_id=expense_id,
                description=f"Expense: {title}"
            )
        
        # Log audit
        await audit_service.log(
            org_id=org_id,
            user_id=created_by,
            action="expense.create",
            resource_type="expense",
            resource_id=expense_id,
            details={"title": title, "amount": amount, "project_id": project_id}
        )
        
        expense.pop("_id", None)
        return expense
    
    async def get_expense(self, expense_id: str) -> Optional[Dict]:
        """Get expense by ID"""
        db = get_database()
        expense = await db.expenses.find_one({"expense_id": expense_id}, {"_id": 0})
        return expense
    
    async def get_expenses_by_project(
        self,
        project_id: str,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get expenses for a project"""
        db = get_database()
        
        query = {"project_id": project_id}
        if category:
            query["category"] = category
        
        expenses = await db.expenses.find(
            query,
            {"_id": 0}
        ).sort("date", -1).skip(offset).limit(limit).to_list(limit)
        
        # Get user names and document titles
        user_ids = list(set([e["created_by"] for e in expenses]))
        doc_ids = list(set([e["document_id"] for e in expenses if e.get("document_id")]))
        
        users_map = {}
        if user_ids:
            users = await db.users.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1}
            ).to_list(len(user_ids))
            users_map = {u["user_id"]: u["name"] for u in users}
        
        docs_map = {}
        if doc_ids:
            docs = await db.documents.find(
                {"document_id": {"$in": doc_ids}},
                {"_id": 0, "document_id": 1, "title": 1}
            ).to_list(len(doc_ids))
            docs_map = {d["document_id"]: d["title"] for d in docs}
        
        for exp in expenses:
            exp["created_by_name"] = users_map.get(exp["created_by"])
            exp["document_title"] = docs_map.get(exp.get("document_id")) if exp.get("document_id") else None
        
        return expenses
    
    async def update_expense(
        self,
        expense_id: str,
        updates: Dict,
        updated_by: str
    ) -> Dict:
        """Update an expense"""
        db = get_database()
        
        expense = await self.get_expense(expense_id)
        if not expense:
            raise ValueError("Expense not found")
        
        old_amount = expense["amount"]
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.expenses.update_one(
            {"expense_id": expense_id},
            {"$set": updates}
        )
        
        # Update budget transaction if amount changed
        if "amount" in updates and updates["amount"] != old_amount:
            budget = await self.get_budget_by_project(expense["project_id"])
            if budget:
                # Delete old transaction and create new one
                await db.budget_transactions.delete_one({
                    "budget_id": budget["budget_id"],
                    "reference_id": expense_id,
                    "source": "expense"
                })
                
                await self.create_transaction(
                    budget_id=budget["budget_id"],
                    source="expense",
                    amount=updates["amount"],
                    created_by=updated_by,
                    reference_id=expense_id,
                    description=f"Expense: {updates.get('title', expense['title'])}"
                )
        
        return await self.get_expense(expense_id)
    
    async def delete_expense(self, expense_id: str, deleted_by: str) -> bool:
        """Delete an expense"""
        db = get_database()
        
        expense = await self.get_expense(expense_id)
        if not expense:
            raise ValueError("Expense not found")
        
        # Delete from budget transactions
        budget = await self.get_budget_by_project(expense["project_id"])
        if budget:
            await db.budget_transactions.delete_one({
                "budget_id": budget["budget_id"],
                "reference_id": expense_id,
                "source": "expense"
            })
            await self.recalculate_budget(budget["budget_id"])
        
        await db.expenses.delete_one({"expense_id": expense_id})
        
        # Log audit
        await audit_service.log(
            org_id=expense["org_id"],
            user_id=deleted_by,
            action="expense.delete",
            resource_type="expense",
            resource_id=expense_id,
            details={"title": expense["title"], "amount": expense["amount"]}
        )
        
        return True
    
    # ==================== Billable Rate Operations ====================
    
    async def set_billable_rate(
        self,
        org_id: str,
        hourly_rate: float,
        currency: str,
        created_by: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        effective_from: Optional[str] = None
    ) -> Dict:
        """Set billable rate for user/project/org"""
        db = get_database()
        
        rate_id = f"rate_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        # Check for existing rate with same scope
        query = {"org_id": org_id, "user_id": user_id, "project_id": project_id}
        existing = await db.billable_rates.find_one(query)
        
        rate = {
            "rate_id": rate_id,
            "org_id": org_id,
            "user_id": user_id,
            "project_id": project_id,
            "hourly_rate": hourly_rate,
            "currency": currency,
            "effective_from": effective_from or now[:10],
            "created_at": now,
            "updated_at": now,
        }
        
        if existing:
            # Update existing rate
            rate["rate_id"] = existing["rate_id"]
            await db.billable_rates.update_one(
                {"rate_id": existing["rate_id"]},
                {"$set": {
                    "hourly_rate": hourly_rate,
                    "currency": currency,
                    "effective_from": effective_from or existing.get("effective_from", now[:10]),
                    "updated_at": now
                }}
            )
        else:
            await db.billable_rates.insert_one(rate)
        
        rate.pop("_id", None)
        return rate
    
    async def get_billable_rate(
        self,
        org_id: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Optional[float]:
        """Get applicable billable rate (most specific first)"""
        db = get_database()
        
        # Try user + project specific rate first
        if user_id and project_id:
            rate = await db.billable_rates.find_one({
                "org_id": org_id,
                "user_id": user_id,
                "project_id": project_id
            }, {"_id": 0})
            if rate:
                return rate["hourly_rate"]
        
        # Try user specific rate
        if user_id:
            rate = await db.billable_rates.find_one({
                "org_id": org_id,
                "user_id": user_id,
                "project_id": None
            }, {"_id": 0})
            if rate:
                return rate["hourly_rate"]
        
        # Try project specific rate
        if project_id:
            rate = await db.billable_rates.find_one({
                "org_id": org_id,
                "user_id": None,
                "project_id": project_id
            }, {"_id": 0})
            if rate:
                return rate["hourly_rate"]
        
        # Fall back to org default
        rate = await db.billable_rates.find_one({
            "org_id": org_id,
            "user_id": None,
            "project_id": None
        }, {"_id": 0})
        
        return rate["hourly_rate"] if rate else None
    
    async def get_billable_rates(self, org_id: str) -> List[Dict]:
        """Get all billable rates for an organization"""
        db = get_database()
        
        rates = await db.billable_rates.find(
            {"org_id": org_id},
            {"_id": 0}
        ).to_list(1000)
        
        # Get user and project names
        user_ids = list(set([r["user_id"] for r in rates if r.get("user_id")]))
        project_ids = list(set([r["project_id"] for r in rates if r.get("project_id")]))
        
        users_map = {}
        if user_ids:
            users = await db.users.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1}
            ).to_list(len(user_ids))
            users_map = {u["user_id"]: u["name"] for u in users}
        
        projects_map = {}
        if project_ids:
            projects = await db.projects.find(
                {"project_id": {"$in": project_ids}},
                {"_id": 0, "project_id": 1, "name": 1}
            ).to_list(len(project_ids))
            projects_map = {p["project_id"]: p["name"] for p in projects}
        
        for rate in rates:
            rate["user_name"] = users_map.get(rate.get("user_id")) if rate.get("user_id") else None
            rate["project_name"] = projects_map.get(rate.get("project_id")) if rate.get("project_id") else None
        
        return rates
    
    # ==================== Time Entry Integration ====================
    
    async def process_time_entry_cost(
        self,
        org_id: str,
        project_id: str,
        task_id: str,
        user_id: str,
        duration_minutes: int,
        time_entry_id: str
    ) -> Optional[Dict]:
        """Process time entry and add cost to budget"""
        db = get_database()
        
        # Get project's budget
        budget = await self.get_budget_by_project(project_id)
        if not budget:
            return None  # No budget for this project
        
        # Get billable rate
        hourly_rate = await self.get_billable_rate(org_id, user_id, project_id)
        if not hourly_rate or hourly_rate == 0:
            return None  # No billable rate configured
        
        # Calculate cost
        hours = duration_minutes / 60
        cost = round(hours * hourly_rate, 2)
        
        # Create transaction
        transaction = await self.create_transaction(
            budget_id=budget["budget_id"],
            source="time_entry",
            amount=cost,
            created_by=user_id,
            reference_id=time_entry_id,
            description=f"Time: {duration_minutes} mins @ {hourly_rate}/hr"
        )
        
        return transaction
    
    async def remove_time_entry_cost(self, time_entry_id: str) -> bool:
        """Remove time entry cost from budget"""
        db = get_database()
        
        transaction = await db.budget_transactions.find_one({
            "reference_id": time_entry_id,
            "source": "time_entry"
        }, {"_id": 0})
        
        if transaction:
            await db.budget_transactions.delete_one({"transaction_id": transaction["transaction_id"]})
            await self.recalculate_budget(transaction["budget_id"])
        
        return True
    
    # ==================== Revision History ====================
    
    async def _create_revision(
        self,
        budget_id: str,
        previous_budget: float,
        new_budget: float,
        reason: Optional[str],
        created_by: str,
        approved_by: Optional[str] = None
    ) -> Dict:
        """Create a budget revision record"""
        db = get_database()
        
        revision_id = f"rev_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        revision = {
            "revision_id": revision_id,
            "budget_id": budget_id,
            "previous_budget": previous_budget,
            "new_budget": new_budget,
            "change_amount": new_budget - previous_budget,
            "reason": reason,
            "approved_by": approved_by,
            "created_at": now,
            "created_by": created_by,
        }
        
        await db.budget_revisions.insert_one(revision)
        revision.pop("_id", None)
        return revision
    
    async def get_revisions(self, budget_id: str) -> List[Dict]:
        """Get revision history for a budget"""
        db = get_database()
        
        revisions = await db.budget_revisions.find(
            {"budget_id": budget_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        
        # Get user names
        user_ids = list(set([r["created_by"] for r in revisions]))
        users_map = {}
        if user_ids:
            users = await db.users.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1}
            ).to_list(len(user_ids))
            users_map = {u["user_id"]: u["name"] for u in users}
        
        for rev in revisions:
            rev["created_by_name"] = users_map.get(rev["created_by"])
        
        return revisions
    
    # ==================== Budget Lock/Unlock ====================
    
    async def check_budget_lock(self, project_id: str) -> Dict:
        """Check if project budget is locked"""
        budget = await self.get_budget_by_project(project_id)
        if not budget:
            return {"is_locked": False, "reason": None}
        
        if budget["status"] == "locked":
            return {
                "is_locked": True,
                "reason": "Budget exceeded and hard limit is enabled",
                "budget_id": budget["budget_id"],
                "spent_percent": budget["spent_percent"]
            }
        
        return {"is_locked": False, "budget_id": budget["budget_id"]}
    
    async def override_lock(self, budget_id: str, overridden_by: str) -> Dict:
        """Override budget lock (admin action)"""
        db = get_database()
        
        budget = await self.get_budget(budget_id)
        if not budget:
            raise ValueError("Budget not found")
        
        if budget["status"] != "locked":
            raise ValueError("Budget is not locked")
        
        # Change status to exceeded (still over budget but not locked)
        await db.project_budgets.update_one(
            {"budget_id": budget_id},
            {"$set": {
                "status": "exceeded",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Log audit
        await audit_service.log(
            org_id=budget["org_id"],
            user_id=overridden_by,
            action="budget.override_lock",
            resource_type="budget",
            resource_id=budget_id,
            details={"project_id": budget["project_id"]}
        )
        
        return await self.get_budget(budget_id)
    
    # ==================== Notifications ====================
    
    async def _send_fifty_percent_notification(
        self,
        budget_id: str,
        spent_percent: float
    ):
        """Send notification when budget reaches 50% threshold"""
        db = get_database()
        
        budget = await self.get_budget(budget_id)
        if not budget:
            return
        
        project = await db.projects.find_one(
            {"project_id": budget["project_id"]},
            {"_id": 0, "name": 1}
        )
        project_name = project["name"] if project else "Unknown"
        
        title = "Budget 50% Alert"
        message = f"Project '{project_name}' has reached {spent_percent:.1f}% of its budget. Half of the budget has been consumed."
        notification_type = "budget_fifty_percent"
        
        # Get project managers and org admins to notify
        memberships = await db.org_memberships.find({
            "org_id": budget["org_id"],
            "role": {"$in": ["org_admin", "super_admin", "project_manager"]}
        }, {"_id": 0, "user_id": 1}).to_list(100)
        
        for member in memberships:
            await notification_service.create(
                user_id=member["user_id"],
                type=notification_type,
                title=title,
                message=message,
                link=f"/projects/{budget['project_id']}?tab=budget",
                send_email=True
            )
        
        logger.info(f"Sent 50% budget notification for budget {budget_id} to {len(memberships)} users")
    
    async def _send_budget_notification(
        self,
        budget_id: str,
        old_status: str,
        new_status: str
    ):
        """Send notification when budget status changes"""
        db = get_database()
        
        budget = await self.get_budget(budget_id)
        if not budget:
            return
        
        project = await db.projects.find_one(
            {"project_id": budget["project_id"]},
            {"_id": 0, "name": 1}
        )
        project_name = project["name"] if project else "Unknown"
        
        # Determine notification type and message
        if new_status == "warning":
            title = "Budget Warning"
            message = f"Project '{project_name}' has exceeded {budget['warning_threshold_percent']}% of its budget."
            notification_type = "budget_warning"
        elif new_status == "exceeded":
            title = "Budget Exceeded"
            message = f"Project '{project_name}' has exceeded 100% of its budget."
            notification_type = "budget_exceeded"
        elif new_status == "locked":
            title = "Budget Locked"
            message = f"Project '{project_name}' budget is locked. Operations are restricted."
            notification_type = "budget_locked"
        else:
            return  # No notification for other status changes
        
        # Get org admins and project managers to notify
        memberships = await db.org_memberships.find({
            "org_id": budget["org_id"],
            "role": {"$in": ["org_admin", "super_admin", "project_manager"]}
        }, {"_id": 0, "user_id": 1}).to_list(100)
        
        for member in memberships:
            await notification_service.create_notification(
                user_id=member["user_id"],
                notification_type=notification_type,
                title=title,
                message=message,
                link=f"/projects/{budget['project_id']}?tab=budget",
                org_id=budget["org_id"],
                send_email=True
            )


# Create singleton instance
budget_service = BudgetService()
