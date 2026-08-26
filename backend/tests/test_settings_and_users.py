import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.auth_service import ensure_seed_user, create_access_token, hash_password
from tests.conftest import get_admin_headers

def get_user_headers(user_id: str, email: str, role: str):
    token = create_access_token({"sub": user_id, "email": email, "role": role})
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_general_profile_get_and_patch(db):
    """Verify GET and PATCH /api/v1/users/me profile persistence."""
    await ensure_seed_user(db)
    
    # 1. Unauthenticated request -> 401
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/users/me")
        assert res.status_code == 401

    # 2. Authenticated GET -> 200
    headers = get_admin_headers()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as ac:
        res = await ac.get("/api/v1/users/me")
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "admin@recovr.ai"
        assert "hashed_password" not in data

        # 3. Authenticated PATCH -> 200
        patch_res = await ac.patch("/api/v1/users/me", json={
            "first_name": "Admin",
            "last_name": "Manager",
            "organization": "Recovr Corp",
            "timezone": "UTC+5:30 (India Standard Time)"
        })
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["first_name"] == "Admin"
        assert updated["last_name"] == "Manager"
        assert updated["organization"] == "Recovr Corp"
        assert updated["timezone"] == "UTC+5:30 (India Standard Time)"

        # 4. Verify persistence across GET reload
        reload_res = await ac.get("/api/v1/users/me")
        assert reload_res.status_code == 200
        reload_data = reload_res.json()
        assert reload_data["organization"] == "Recovr Corp"

@pytest.mark.asyncio
async def test_notification_preferences_get_and_patch(db):
    """Verify GET and PATCH /api/v1/users/me/notifications persistence."""
    await ensure_seed_user(db)
    headers = get_admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as ac:
        # GET default preferences
        res = await ac.get("/api/v1/users/me/notifications")
        assert res.status_code == 200
        prefs = res.json()
        assert prefs["recovery_alerts"] is True

        # PATCH updated preferences
        patch_res = await ac.patch("/api/v1/users/me/notifications", json={
            "recovery_alerts": False,
            "payment_failures": True,
            "weekly_digest": True,
            "system_updates": False,
            "realtime_alerts": True,
            "audit_log_events": True,
            "api_key_activity": False
        })
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["recovery_alerts"] is False
        assert updated["weekly_digest"] is True
        assert updated["api_key_activity"] is False

        # Read back persisted preferences
        reload_res = await ac.get("/api/v1/users/me/notifications")
        assert reload_res.status_code == 200
        assert reload_res.json()["recovery_alerts"] is False

@pytest.mark.asyncio
async def test_change_password_security(db):
    """Verify password change authentication security."""
    await ensure_seed_user(db)
    headers = get_admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as ac:
        # Wrong current password -> 400
        wrong_res = await ac.post("/api/v1/auth/change-password", json={
            "current_password": "WrongPassword999",
            "new_password": "NewSecretPassword123"
        })
        assert wrong_res.status_code == 400

        # Correct current password -> 200
        correct_res = await ac.post("/api/v1/auth/change-password", json={
            "current_password": "Admin@123456",
            "new_password": "NewSecretPassword123"
        })
        assert correct_res.status_code == 200
        assert correct_res.json()["success"] is True

        # Login with new password -> 200
        login_res = await ac.post("/api/v1/auth/login", json={
            "email": "admin@recovr.ai",
            "password": "NewSecretPassword123"
        })
        assert login_res.status_code == 200

@pytest.mark.asyncio
async def test_team_rbac_permissions(db):
    """Verify Team management APIs enforce ADMIN role restrictions."""
    await ensure_seed_user(db)
    
    # Seed an Operator user and a Viewer user
    op_id = f"usr_op_{uuid.uuid4().hex[:6]}"
    await db["users"].insert_one({
        "_id": op_id,
        "email": "operator@recovr.ai",
        "name": "Operator User",
        "hashed_password": hash_password("Operator@123"),
        "role": "OPERATOR",
        "is_active": True
    })

    admin_headers = get_admin_headers()
    op_headers = get_user_headers(op_id, "operator@recovr.ai", "OPERATOR")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Operator tries to list users -> 403 Forbidden
        op_list = await ac.get("/api/v1/users", headers=op_headers)
        assert op_list.status_code == 403

        # Admin lists users -> 200 OK
        admin_list = await ac.get("/api/v1/users", headers=admin_headers)
        assert admin_list.status_code == 200
        assert len(admin_list.json()) >= 2

        # Operator tries to create user -> 403 Forbidden
        op_create = await ac.post("/api/v1/users", json={
            "email": "newbie@recovr.ai", "name": "New User", "role": "OPERATOR"
        }, headers=op_headers)
        assert op_create.status_code == 403

        # Admin creates user -> 201 Created
        admin_create = await ac.post("/api/v1/users", json={
            "email": "newbie@recovr.ai", "name": "New User", "role": "OPERATOR"
        }, headers=admin_headers)
        assert admin_create.status_code == 201
        created_user = admin_create.json()["user"]
        created_id = created_user["id"]
        assert "temporary_password" in admin_create.json()

        # Admin changes role -> 200 OK
        role_change = await ac.patch(f"/api/v1/users/{created_id}", json={"role": "ADMIN"}, headers=admin_headers)
        assert role_change.status_code == 200
        assert role_change.json()["role"] == "ADMIN"

        # Admin deletes created user -> 200 OK
        del_res = await ac.delete(f"/api/v1/users/{created_id}", headers=admin_headers)
        assert del_res.status_code == 200
