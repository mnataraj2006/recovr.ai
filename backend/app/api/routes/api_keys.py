import secrets
import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.db.connection import get_db
from app.api.dependencies import require_role, get_current_user
from app.audit.logger import log_audit_event

router = APIRouter()

class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=64, description="Friendly name for the API Key")

class ApiKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    masked_key: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    status: str

class CreateApiKeyResponse(ApiKeyResponse):
    secret: str = Field(..., description="Full secret API Key string. Discarded after creation and cannot be retrieved again.")

def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(
    db = Depends(get_db),
    current_user: dict = Depends(require_role(["ADMIN", "OPERATOR"]))
):
    """Lists all API keys for tenant with masked secrets."""
    cursor = db["api_keys"].find({}).sort("created_at", -1)
    keys = await cursor.to_list(length=100)
    result = []
    for item in keys:
        item_id = str(item.pop("_id"))
        result.append(ApiKeyResponse(
            id=item_id,
            name=item.get("name", "API Key"),
            prefix=item.get("prefix", "sk_live_"),
            masked_key=item.get("masked_key", "sk_live_••••••••"),
            created_at=item.get("created_at", datetime.now(timezone.utc)),
            last_used_at=item.get("last_used_at"),
            revoked_at=item.get("revoked_at"),
            status=item.get("status", "ACTIVE")
        ))
    return result

@router.post("/api-keys", response_model=CreateApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    req: CreateApiKeyRequest,
    db = Depends(get_db),
    current_user: dict = Depends(require_role(["ADMIN"]))
):
    """Generates a new cryptographically secure API key. Shows full secret ONLY ONCE."""
    key_id = f"key_{uuid.uuid4().hex[:8]}"
    random_bytes = secrets.token_hex(24)
    raw_secret = f"sk_live_{random_bytes}"
    prefix = raw_secret[:12]
    masked_key = f"{prefix}••••••••{raw_secret[-4:]}"
    key_hash = hash_api_key(raw_secret)
    now = datetime.now(timezone.utc)

    doc = {
        "_id": key_id,
        "name": req.name,
        "prefix": prefix,
        "masked_key": masked_key,
        "key_hash": key_hash,
        "created_by": current_user["id"],
        "created_at": now,
        "last_used_at": None,
        "revoked_at": None,
        "status": "ACTIVE"
    }
    await db["api_keys"].insert_one(doc)

    await log_audit_event(
        transaction_id="SYSTEM",
        event_type="API_KEY_CREATED",
        actor="USER",
        source="ApiKeyRouter",
        reason=f"API Key '{req.name}' created by {current_user['email']}",
        metadata={"key_id": key_id, "name": req.name, "created_by": current_user["email"]}
    )

    return CreateApiKeyResponse(
        id=key_id,
        name=req.name,
        prefix=prefix,
        masked_key=masked_key,
        secret=raw_secret,
        created_at=now,
        status="ACTIVE"
    )

@router.post("/api-keys/{key_id}/revoke", response_model=ApiKeyResponse)
async def revoke_api_key(
    key_id: str,
    db = Depends(get_db),
    current_user: dict = Depends(require_role(["ADMIN"]))
):
    """Revokes an existing active API key."""
    key_doc = await db["api_keys"].find_one({"_id": key_id})
    if not key_doc:
        raise HTTPException(status_code=404, detail="API Key not found.")

    if key_doc.get("status") == "REVOKED":
        raise HTTPException(status_code=400, detail="API Key is already revoked.")

    now = datetime.now(timezone.utc)
    await db["api_keys"].update_one(
        {"_id": key_id},
        {"$set": {"status": "REVOKED", "revoked_at": now}}
    )

    await log_audit_event(
        transaction_id="SYSTEM",
        event_type="API_KEY_REVOKED",
        actor="USER",
        source="ApiKeyRouter",
        reason=f"API Key '{key_doc.get('name')}' revoked by {current_user['email']}",
        metadata={"key_id": key_id, "revoked_by": current_user["email"]}
    )

    key_doc["id"] = str(key_doc.pop("_id"))
    key_doc["status"] = "REVOKED"
    key_doc["revoked_at"] = now
    return ApiKeyResponse(**key_doc)

@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    db = Depends(get_db),
    current_user: dict = Depends(require_role(["ADMIN"]))
):
    """Deletes an API key record."""
    res = await db["api_keys"].delete_one({"_id": key_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="API Key not found.")

    await log_audit_event(
        transaction_id="SYSTEM",
        event_type="API_KEY_DELETED",
        actor="USER",
        source="ApiKeyRouter",
        reason=f"API Key {key_id} deleted by {current_user['email']}",
        metadata={"key_id": key_id}
    )
