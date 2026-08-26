import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict

import jwt
from passlib.context import CryptContext
from app.config.settings import settings
from app.audit.logger import log_audit_event

logger = logging.getLogger(__name__)

import bcrypt

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("AuthService: Expired JWT token presented.")
        return None
    except jwt.PyJWTError as e:
        logger.warning(f"AuthService: Invalid JWT token presented: {e}")
        return None

async def ensure_seed_user(db):
    """Ensures at least one seed admin user exists for initial login."""
    try:
        user_count = await db["users"].count_documents({})
        if user_count == 0:
            seed_user = {
                "_id": f"usr_{uuid.uuid4().hex[:8]}",
                "email": "admin@recovr.ai",
                "name": "Admin User",
                "hashed_password": hash_password("Admin@123456"),
                "role": "ADMIN",
                "created_at": datetime.now(timezone.utc),
                "is_active": True,
            }
            await db["users"].insert_one(seed_user)
            logger.info("AuthService: Created default seed admin user (admin@recovr.ai).")
    except Exception as e:
        logger.error(f"AuthService: Failed to create seed admin user: {e}")
