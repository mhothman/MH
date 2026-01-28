"""Customer Repository - Data access layer for customers"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from core.database import get_database
from repositories import BaseRepository


class CustomerRepository(BaseRepository):
    """Repository for customer data access"""
    
    @property
    def collection_name(self) -> str:
        return "customers"
    
    @property
    def id_field(self) -> str:
        return "customer_id"
    
    async def find_by_id(self, customer_id: str) -> Optional[Dict]:
        """Find customer by ID"""
        db = get_database()
        return await db.customers.find_one({self.id_field: customer_id}, {"_id": 0})
    
    async def find_all(self, query: Dict = None, limit: int = 500) -> List[Dict]:
        """Find all customers matching query"""
        db = get_database()
        return await db.customers.find(query or {}, {"_id": 0}).sort("name", 1).to_list(limit)
    
    async def find_by_org(self, org_id: str) -> List[Dict]:
        """Find customers by organization"""
        db = get_database()
        return await db.customers.find({"org_id": org_id}, {"_id": 0}).sort("name", 1).to_list(500)
    
    async def find_by_email(self, email: str, org_id: str) -> Optional[Dict]:
        """Find customer by email within organization"""
        db = get_database()
        return await db.customers.find_one(
            {"email": email, "org_id": org_id},
            {"_id": 0}
        )
    
    async def create(self, data: Dict) -> Dict:
        """Create a new customer"""
        db = get_database()
        customer_id = f"cust_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        customer = {
            "customer_id": customer_id,
            **data,
            "created_at": now,
            "updated_at": now
        }
        
        await db.customers.insert_one(customer)
        customer.pop("_id", None)
        return customer
    
    async def update(self, customer_id: str, data: Dict) -> bool:
        """Update a customer"""
        db = get_database()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await db.customers.update_one(
            {self.id_field: customer_id},
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def delete(self, customer_id: str) -> bool:
        """Delete a customer"""
        db = get_database()
        result = await db.customers.delete_one({self.id_field: customer_id})
        return result.deleted_count > 0
    
    async def count_by_org(self, org_id: str) -> int:
        """Count customers in an organization"""
        db = get_database()
        return await db.customers.count_documents({"org_id": org_id})
    
    async def get_with_project_counts(self, org_id: str) -> List[Dict]:
        """Get customers with their project counts"""
        db = get_database()
        
        customers = await self.find_by_org(org_id)
        if not customers:
            return []
        
        customer_ids = [c["customer_id"] for c in customers]
        
        # Get project counts in bulk
        project_counts = await db.projects.aggregate([
            {"$match": {"customer_id": {"$in": customer_ids}}},
            {"$group": {"_id": "$customer_id", "count": {"$sum": 1}}}
        ]).to_list(len(customer_ids))
        
        counts_map = {pc["_id"]: pc["count"] for pc in project_counts}
        
        for customer in customers:
            customer["project_count"] = counts_map.get(customer["customer_id"], 0)
        
        return customers
    
    async def search(self, org_id: str, query: str, limit: int = 20) -> List[Dict]:
        """Search customers by name or email"""
        db = get_database()
        return await db.customers.find(
            {
                "org_id": org_id,
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"email": {"$regex": query, "$options": "i"}},
                    {"company": {"$regex": query, "$options": "i"}}
                ]
            },
            {"_id": 0}
        ).limit(limit).to_list(limit)


# Singleton instance
customer_repository = CustomerRepository()
