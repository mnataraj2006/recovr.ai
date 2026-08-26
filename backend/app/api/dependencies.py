from typing import List, Optional
import hashlib
import logging
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db.connection import get_db
from app.services.auth_service import decode_access_token

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

async def get_authenticated_principal(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db = Depends(get_db)
) -> dict:
    """
    Unified authentication dependency supporting both stateless JWT Bearer tokens
    and cryptographically hashed API Keys (passed via Bearer token 'sk_live_...' or X-API-Key header).
    Returns a unified principal dictionary containing user/token identity and role.
    """
    token_candidate = None
    if credentials and credentials.credentials:
        token_candidate = credentials.credentials
    elif x_api_key:
        token_candidate = x_api_key

    if not token_candidate:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required (JWT Bearer token or API Key).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. API Key Authentication (starts with 'sk_live_')
    if token_candidate.startswith("sk_live_"):
        key_hash = hashlib.sha256(token_candidate.encode('utf-8')).hexdigest()
        key_doc = await db["api_keys"].find_one({"key_hash": key_hash, "status": "ACTIVE"})
        if not key_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, missing, or revoked API Key.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check expiration if configured
        if key_doc.get("expires_at"):
            exp_time = key_doc["expires_at"]
            if isinstance(exp_time, str):
                exp_time = datetime.fromisoformat(exp_time.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp_time:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Expired API Key.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Update last_used_at safely
        now = datetime.now(timezone.utc)
        await db["api_keys"].update_one(
            {"_id": key_doc["_id"]},
            {"$set": {"last_used_at": now}}
        )

        return {
            "id": key_doc.get("created_by", "system"),
            "email": f"api_key:{key_doc['_id']}",
            "role": "ADMIN",
            "auth_type": "API_KEY",
            "api_key_id": key_doc["_id"]
        }

    # 2. JWT Authentication
    payload = decode_access_token(token_candidate)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    user = await db["users"].find_one({"_id": user_id, "is_active": True})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_dict = dict(user)
    user_dict["id"] = user_dict.pop("_id")
    user_dict.pop("hashed_password", None)
    user_dict["auth_type"] = "JWT"
    return user_dict

async def get_current_user(principal: dict = Depends(get_authenticated_principal)) -> dict:
    """Alias for backwards compatibility with get_current_user dependencies."""
    return principal

def require_role(allowed_roles: List[str]):
    async def role_checker(principal: dict = Depends(get_authenticated_principal)) -> dict:
        user_role = principal.get("role", "VIEWER").upper()
        allowed_upper = [r.upper() for r in allowed_roles]
        if user_role not in allowed_upper:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Requires one of roles {allowed_roles}. Current role: {user_role}"
            )
        return principal
    return role_checker
