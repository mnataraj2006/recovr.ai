from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.db.connection import get_db
from app.api.dependencies import get_current_user, require_role
from app.services.auth_service import hash_password
from app.audit.logger import log_audit_event

router = APIRouter()

class UserProfileResponse(BaseModel):
    id: str
    email: str
    name: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    organization: Optional[str] = ""
    timezone: Optional[str] = "UTC (Coordinated Universal Time)"
    role: str
    is_active: bool = True
    created_at: Optional[datetime] = None

class UserProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    organization: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=100)

class NotificationPreferences(BaseModel):
    recovery_alerts: bool = True
    payment_failures: bool = True
    weekly_digest: bool = False
    system_updates: bool = True
    realtime_alerts: bool = True
    audit_log_events: bool = False
    api_key_activity: bool = True

class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    role: str = Field("OPERATOR", pattern="^(ADMIN|OPERATOR|VIEWER)$")

class UpdateUserRequest(BaseModel):
    role: Optional[str] = Field(None, pattern="^(ADMIN|OPERATOR|VIEWER)$")
    is_active: Optional[bool] = None

@router.get("/users/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    user_doc = await db["users"].find_one({"_id": current_user["id"]})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User profile not found.")
    
    return UserProfileResponse(
        id=str(user_doc["_id"]),
        email=user_doc.get("email", ""),
        name=user_doc.get("name", "User"),
        first_name=user_doc.get("first_name", ""),
        last_name=user_doc.get("last_name", ""),
        organization=user_doc.get("organization", ""),
        timezone=user_doc.get("timezone", "UTC (Coordinated Universal Time)"),
        role=user_doc.get("role", "VIEWER"),
        is_active=user_doc.get("is_active", True),
        created_at=user_doc.get("created_at")
    )

@router.patch("/users/me", response_model=UserProfileResponse)
async def update_my_profile(
    req: UserProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    user_id = current_user["id"]
    user_doc = await db["users"].find_one({"_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User profile not found.")

    update_fields = {}
    if req.first_name is not None:
        update_fields["first_name"] = req.first_name.strip()
    if req.last_name is not None:
        update_fields["last_name"] = req.last_name.strip()
    if req.first_name is not None or req.last_name is not None:
        fname = update_fields.get("first_name", user_doc.get("first_name", ""))
        lname = update_fields.get("last_name", user_doc.get("last_name", ""))
        update_fields["name"] = f"{fname} {lname}".strip() or user_doc.get("name", "User")
    if req.organization is not None:
        update_fields["organization"] = req.organization.strip()
    if req.timezone is not None:
        update_fields["timezone"] = req.timezone.strip()

    if req.email is not None:
        new_email = req.email.lower().strip()
        if new_email != user_doc.get("email"):
            existing = await db["users"].find_one({"email": new_email, "_id": {"$ne": user_id}})
            if existing:
                raise HTTPException(status_code=400, detail="Email address is already in use by another account.")
            update_fields["email"] = new_email

    if update_fields:
        await db["users"].update_one({"_id": user_id}, {"$set": update_fields})
        await log_audit_event(
            transaction_id="SYSTEM",
            event_type="USER_PROFILE_UPDATED",
            actor="USER",
            source="UsersAPI",
            reason=f"User {user_id} updated profile details.",
            metadata={"updated_fields": list(update_fields.keys()), "user_id": user_id}
        )

    updated_doc = await db["users"].find_one({"_id": user_id})
    return UserProfileResponse(
        id=str(updated_doc["_id"]),
        email=updated_doc.get("email", ""),
        name=updated_doc.get("name", "User"),
        first_name=updated_doc.get("first_name", ""),
        last_name=updated_doc.get("last_name", ""),
        organization=updated_doc.get("organization", ""),
        timezone=updated_doc.get("timezone", "UTC (Coordinated Universal Time)"),
        role=updated_doc.get("role", "VIEWER"),
        is_active=updated_doc.get("is_active", True),
        created_at=updated_doc.get("created_at")
    )

@router.get("/users/me/notifications", response_model=NotificationPreferences)
async def get_my_notification_preferences(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    user_doc = await db["users"].find_one({"_id": current_user["id"]})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User profile not found.")
    
    prefs = user_doc.get("notification_preferences", {})
    return NotificationPreferences(**prefs)

@router.patch("/users/me/notifications", response_model=NotificationPreferences)
async def update_my_notification_preferences(
    req: NotificationPreferences,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    user_id = current_user["id"]
    prefs_data = req.model_dump()
    
    await db["users"].update_one(
        {"_id": user_id},
        {"$set": {"notification_preferences": prefs_data}}
    )
    
    await log_audit_event(
        transaction_id="SYSTEM",
        event_type="USER_NOTIFICATIONS_UPDATED",
        actor="USER",
        source="UsersAPI",
        reason=f"User {user_id} updated notification preferences.",
        metadata={"user_id": user_id}
    )

    return NotificationPreferences(**prefs_data)

@router.get("/users", response_model=List[UserProfileResponse])
async def list_users(
    db = Depends(get_db),
    current_user: dict = Depends(require_role(["ADMIN"]))
):
    cursor = db["users"].find({}).sort("created_at", -1)
    users = []
    async for u in cursor:
        users.append(UserProfileResponse(
            id=str(u["_id"]),
            email=u.get("email", ""),
            name=u.get("name", "User"),
            first_name=u.get("first_name", ""),
            last_name=u.get("last_name", ""),
            organization=u.get("organization", ""),
            timezone=u.get("timezone", "UTC (Coordinated Universal Time)"),
            role=u.get("role", "VIEWER"),
            is_active=u.get("is_active", True),
            created_at=u.get("created_at")
        ))
    return users

class CreateUserResponse(BaseModel):
    user: UserProfileResponse
    temporary_password: str

@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=CreateUserResponse)
async def create_user(
    req: CreateUserRequest,
    db = Depends(get_db),
    current_user: dict = Depends(require_role(["ADMIN"]))
):
    email_clean = req.email.lower().strip()
    existing = await db["users"].find_one({"email": email_clean})
    if existing:
        raise HTTPException(status_code=400, detail="User account with this email already exists.")

    temp_password = f"Recovr#{uuid.uuid4().hex[:6]}"
    user_id = f"usr_{uuid.uuid4().hex[:8]}"

    new_user = {
        "_id": user_id,
        "email": email_clean,
        "name": req.name.strip(),
        "hashed_password": hash_password(temp_password),
        "role": req.role,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user["id"]
    }
    await db["users"].insert_one(new_user)

    await log_audit_event(
        transaction_id="SYSTEM",
        event_type="USER_CREATED",
        actor="ADMIN",
        source="UsersAPI",
        reason=f"Admin created new user account {email_clean} with role {req.role}",
        metadata={"created_user_id": user_id, "role": req.role}
    )

    user_resp = UserProfileResponse(
        id=user_id,
        email=email_clean,
        name=req.name.strip(),
        role=req.role,
        is_active=True,
        created_at=new_user["created_at"]
    )
    return CreateUserResponse(user=user_resp, temporary_password=temp_password)

@router.patch("/users/{user_id}", response_model=UserProfileResponse)
async def update_user(
    user_id: str,
    req: UpdateUserRequest,
    db = Depends(get_db),
    current_user: dict = Depends(require_role(["ADMIN"]))
):
    user_doc = await db["users"].find_one({"_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")

    update_fields = {}
    if req.role is not None:
        update_fields["role"] = req.role
    if req.is_active is not None:
        update_fields["is_active"] = req.is_active

    if update_fields:
        await db["users"].update_one({"_id": user_id}, {"$set": update_fields})
        await log_audit_event(
            transaction_id="SYSTEM",
            event_type="USER_UPDATED",
            actor="ADMIN",
            source="UsersAPI",
            reason=f"Admin updated user {user_id} fields: {list(update_fields.keys())}",
            metadata={"target_user_id": user_id, "updates": update_fields}
        )

    updated_doc = await db["users"].find_one({"_id": user_id})
    return UserProfileResponse(
        id=str(updated_doc["_id"]),
        email=updated_doc.get("email", ""),
        name=updated_doc.get("name", "User"),
        first_name=updated_doc.get("first_name", ""),
        last_name=updated_doc.get("last_name", ""),
        organization=updated_doc.get("organization", ""),
        timezone=updated_doc.get("timezone", "UTC (Coordinated Universal Time)"),
        role=updated_doc.get("role", "VIEWER"),
        is_active=updated_doc.get("is_active", True),
        created_at=updated_doc.get("created_at")
    )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db = Depends(get_db),
    current_user: dict = Depends(require_role(["ADMIN"]))
):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account.")

    user_doc = await db["users"].find_one({"_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")

    await db["users"].delete_one({"_id": user_id})
    await log_audit_event(
        transaction_id="SYSTEM",
        event_type="USER_DELETED",
        actor="ADMIN",
        source="UsersAPI",
        reason=f"Admin deleted user {user_doc.get('email')} ({user_id})",
        metadata={"deleted_user_id": user_id, "email": user_doc.get("email")}
    )

    return {"success": True, "deleted_user_id": user_id}
