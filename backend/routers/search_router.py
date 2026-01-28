"""Global search router"""
from fastapi import APIRouter, HTTPException, Request, Query
from datetime import datetime, timezone
from typing import Optional, List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, get_user_org_membership

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def global_search(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query"),
    org_id: Optional[str] = None,
    type: Optional[str] = Query(None, description="Filter by type: task, project, customer, comment"),
    limit: int = Query(20, le=50)
):
    """
    Global search across projects, tasks, customers, and comments.
    
    Results are scoped to user's organizations.
    """
    db = get_database()
    user = await require_auth(request)
    
    # Get user's organizations
    if org_id:
        membership = await get_user_org_membership(user["user_id"], org_id)
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        org_ids = [org_id]
    else:
        memberships = await db.org_memberships.find(
            {"user_id": user["user_id"]},
            {"_id": 0, "org_id": 1}
        ).to_list(100)
        org_ids = [m["org_id"] for m in memberships]
    
    if not org_ids:
        return {"results": [], "total": 0}
    
    results = []
    search_regex = {"$regex": q, "$options": "i"}
    
    # Search projects
    if not type or type == "project":
        projects = await db.projects.find({
            "org_id": {"$in": org_ids},
            "$or": [
                {"name": search_regex},
                {"description": search_regex}
            ]
        }, {"_id": 0}).limit(limit).to_list(limit)
        
        for p in projects:
            results.append({
                "type": "project",
                "id": p["project_id"],
                "title": p["name"],
                "description": p.get("description"),
                "status": p.get("status"),
                "link": f"/projects/{p['project_id']}",
                "created_at": p.get("created_at")
            })
    
    # Search tasks
    if not type or type == "task":
        # Get project IDs for user's orgs
        projects = await db.projects.find(
            {"org_id": {"$in": org_ids}},
            {"project_id": 1, "name": 1}
        ).to_list(None)
        project_map = {p["project_id"]: p["name"] for p in projects}
        project_ids = list(project_map.keys())
        
        tasks = await db.tasks.find({
            "project_id": {"$in": project_ids},
            "$or": [
                {"title": search_regex},
                {"description": search_regex}
            ]
        }, {"_id": 0}).limit(limit).to_list(limit)
        
        for t in tasks:
            results.append({
                "type": "task",
                "id": t["task_id"],
                "title": t["title"],
                "description": t.get("description"),
                "status": t.get("status"),
                "priority": t.get("priority"),
                "project_id": t["project_id"],
                "project_name": project_map.get(t["project_id"]),
                "link": f"/projects/{t['project_id']}?task={t['task_id']}",
                "created_at": t.get("created_at")
            })
    
    # Search customers
    if not type or type == "customer":
        customers = await db.customers.find({
            "org_id": {"$in": org_ids},
            "$or": [
                {"name": search_regex},
                {"email": search_regex},
                {"company": search_regex}
            ]
        }, {"_id": 0}).limit(limit).to_list(limit)
        
        for c in customers:
            results.append({
                "type": "customer",
                "id": c["customer_id"],
                "title": c["name"],
                "description": c.get("company"),
                "link": f"/customers/{c['customer_id']}",
                "created_at": c.get("created_at")
            })
    
    # Search comments
    if not type or type == "comment":
        comments = await db.comments.find({
            "org_id": {"$in": org_ids},
            "content": search_regex
        }, {"_id": 0}).limit(limit).to_list(limit)
        
        for c in comments:
            link = f"/projects/{c.get('project_id')}"
            if c.get("task_id"):
                link += f"?task={c['task_id']}"
            
            results.append({
                "type": "comment",
                "id": c["comment_id"],
                "title": c["content"][:100] + "..." if len(c.get("content", "")) > 100 else c.get("content"),
                "task_id": c.get("task_id"),
                "project_id": c.get("project_id"),
                "link": link,
                "created_at": c.get("created_at")
            })
    
    # Sort by relevance (exact match first, then by created_at)
    results.sort(key=lambda x: (
        0 if q.lower() in str(x.get("title", "")).lower() else 1,
        x.get("created_at", "") or ""
    ), reverse=True)
    
    return {
        "results": results[:limit],
        "total": len(results),
        "query": q
    }
