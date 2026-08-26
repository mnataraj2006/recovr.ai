from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from app.db.connection import get_db
from app.services.auth_service import verify_password, create_access_token, hash_password
from app.api.dependencies import get_current_user
from app.audit.logger import log_audit_event

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

@router.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest, db = Depends(get_db)):
    """Authenticates user credentials and returns JWT access token."""
    email_clean = req.email.lower().strip()
    user = await db["users"].find_one({"email": email_clean})
    
    if not user or not verify_password(req.password, user.get("hashed_password", "")):
        await log_audit_event(
            transaction_id="SYSTEM",
            event_type="USER_LOGIN_FAILED",
            actor="SYSTEM",
            source="AuthRouter",
            reason=f"Failed login attempt for email {email_clean}",
            metadata={"email": email_clean}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated."
        )

    user_id = str(user["_id"])
    role = user.get("role", "VIEWER")
    
    token = create_access_token(data={"sub": user_id, "email": email_clean, "role": role})

    await log_audit_event(
        transaction_id="SYSTEM",
        event_type="USER_LOGIN_SUCCESS",
        actor="USER",
        source="AuthRouter",
        reason=f"Successful authentication for user {email_clean} (Role: {role})",
        metadata={"user_id": user_id, "role": role}
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user_id,
            email=email_clean,
            name=user.get("name", "User"),
            role=role
        )
    )

@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Returns profile for currently authenticated user."""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user.get("name", "User"),
        role=current_user.get("role", "VIEWER")
    )

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

@router.post("/auth/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Securely updates password for authenticated user."""
    user_id = current_user["id"]
    user_doc = await db["users"].find_one({"_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User account not found.")

    if not verify_password(req.current_password, user_doc.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    new_hash = hash_password(req.new_password)
    await db["users"].update_one({"_id": user_id}, {"$set": {"hashed_password": new_hash}})

    await log_audit_event(
        transaction_id="SYSTEM",
        event_type="USER_PASSWORD_CHANGED",
        actor="USER",
        source="AuthRouter",
        reason=f"User {user_id} changed account password.",
        metadata={"user_id": user_id}
    )

    return {"success": True, "message": "Password changed successfully."}

