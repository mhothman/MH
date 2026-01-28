"""Comment router for task/project comments"""
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import logging
import re

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, get_user_org_membership, check_permission
from core.permissions import Permission, has_permission
from services.notification_service import notification_service
from services.audit_service import audit_service
from models.comment import CommentCreate, CommentUpdate, CommentResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def get_comments(
    request: Request,
    task_id: Optional[str] = None,
    project_id: Optional[str] = None
):
    """Get comments for a task or project"""
    db = get_database()
    user = await require_auth(request)
    
    query = {}
    if task_id:
        task = await db.tasks.find_one({"task_id": task_id}, {"_id": 0})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        membership = await get_user_org_membership(user["user_id"], task["org_id"])
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check COMMENT_VIEW permission
        if not has_permission(membership["role"], Permission.COMMENT_VIEW):
            raise HTTPException(status_code=403, detail="Permission denied: cannot view comments")
        
        query["task_id"] = task_id
    elif project_id:
        project = await db.projects.find_one({"project_id": project_id}, {"_id": 0})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        membership = await get_user_org_membership(user["user_id"], project["org_id"])
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check COMMENT_VIEW permission
        if not has_permission(membership["role"], Permission.COMMENT_VIEW):
            raise HTTPException(status_code=403, detail="Permission denied: cannot view comments")
        
        query["project_id"] = project_id
    else:
        raise HTTPException(status_code=400, detail="task_id or project_id required")
    
    comments = await db.comments.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    # Add author info
    for comment in comments:
        author = await db.users.find_one({"user_id": comment["author_id"]}, {"_id": 0, "name": 1, "picture": 1})
        if author:
            comment["author_name"] = author.get("name", "Unknown")
            comment["author_picture"] = author.get("picture")
        else:
            comment["author_name"] = "Unknown"
            comment["author_picture"] = None
        
        comment["created_at"] = datetime.fromisoformat(comment["created_at"]) if isinstance(comment["created_at"], str) else comment["created_at"]
        comment["updated_at"] = datetime.fromisoformat(comment.get("updated_at", comment["created_at"])) if isinstance(comment.get("updated_at"), str) else comment.get("updated_at", comment["created_at"])
    
    return comments

@router.post("/")
async def create_comment(data: CommentCreate, request: Request):
    """Create a new comment"""
    db = get_database()
    user = await require_auth(request)
    
    org_id = None
    link = None
    
    if data.task_id:
        task = await db.tasks.find_one({"task_id": data.task_id}, {"_id": 0})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        membership = await get_user_org_membership(user["user_id"], task["org_id"])
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check COMMENT_CREATE permission
        if not has_permission(membership["role"], Permission.COMMENT_CREATE):
            raise HTTPException(status_code=403, detail="Permission denied: cannot create comments")
        
        org_id = task["org_id"]
        link = f"/projects/{task['project_id']}?task={data.task_id}"
    elif data.project_id:
        project = await db.projects.find_one({"project_id": data.project_id}, {"_id": 0})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        membership = await get_user_org_membership(user["user_id"], project["org_id"])
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check COMMENT_CREATE permission
        if not has_permission(membership["role"], Permission.COMMENT_CREATE):
            raise HTTPException(status_code=403, detail="Permission denied: cannot create comments")
        
        org_id = project["org_id"]
        link = f"/projects/{data.project_id}"
    else:
        raise HTTPException(status_code=400, detail="task_id or project_id required")
    
    comment_id = f"comm_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
    comment = {
        "comment_id": comment_id,
        "content": data.content,
        "task_id": data.task_id,
        "project_id": data.project_id,
        "org_id": org_id,
        "author_id": user["user_id"],
        "mentions": data.mentions,
        "created_at": now,
        "updated_at": now
    }
    
    await db.comments.insert_one(comment)
    
    # Remove MongoDB _id from response
    comment.pop("_id", None)
    
    # Process mentions - extract @mentions from content if not provided
    mentions = data.mentions
    if not mentions:
        mention_pattern = r'@(\w+)'
        mentions_in_content = re.findall(mention_pattern, data.content)
        if mentions_in_content:
            # Try to find users by name
            for name in mentions_in_content:
                mentioned_user = await db.users.find_one(
                    {"name": {"$regex": name, "$options": "i"}},
                    {"_id": 0, "user_id": 1}
                )
                if mentioned_user and mentioned_user["user_id"] not in mentions:
                    mentions.append(mentioned_user["user_id"])
    
    # Notify mentioned users
    for mention_id in mentions:
        if mention_id != user["user_id"]:
            await notification_service.create(
                user_id=mention_id,
                type="mention",
                title=f"{user['name']} mentioned you",
                message=f"In a comment: {data.content[:100]}...",
                link=link
            )
    
    await audit_service.log(user["user_id"], org_id, "create", "comment", comment_id)
    
    # Return with author info
    comment["author_name"] = user.get("name", "Unknown")
    comment["author_picture"] = user.get("picture")
    comment["created_at"] = datetime.fromisoformat(comment["created_at"])
    comment["updated_at"] = datetime.fromisoformat(comment["updated_at"])
    
    return comment

@router.put("/{comment_id}")
async def update_comment(comment_id: str, data: CommentUpdate, request: Request):
    """Update a comment"""
    db = get_database()
    user = await require_auth(request)
    
    comment = await db.comments.find_one({"comment_id": comment_id}, {"_id": 0})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    membership = await get_user_org_membership(user["user_id"], comment["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Only author can edit (using COMMENT_EDIT_OWN permission)
    if comment["author_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Only the author can edit this comment")
    
    if not has_permission(membership["role"], Permission.COMMENT_EDIT_OWN):
        raise HTTPException(status_code=403, detail="Permission denied: cannot edit comments")
    
    await db.comments.update_one(
        {"comment_id": comment_id},
        {"$set": {
            "content": data.content,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Comment updated"}

@router.delete("/{comment_id}")
async def delete_comment(comment_id: str, request: Request):
    """Delete a comment"""
    db = get_database()
    user = await require_auth(request)
    
    comment = await db.comments.find_one({"comment_id": comment_id}, {"_id": 0})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Author or admin can delete
    membership = await get_user_org_membership(user["user_id"], comment["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    is_author = comment["author_id"] == user["user_id"]
    can_delete_any = has_permission(membership["role"], Permission.COMMENT_DELETE_ANY)
    can_edit_own = has_permission(membership["role"], Permission.COMMENT_EDIT_OWN)
    
    if not can_delete_any and not (is_author and can_edit_own):
        raise HTTPException(status_code=403, detail="Permission denied: cannot delete this comment")
    
    await db.comments.delete_one({"comment_id": comment_id})
    
    await audit_service.log(user["user_id"], comment["org_id"], "delete", "comment", comment_id)
    
    return {"message": "Comment deleted"}
