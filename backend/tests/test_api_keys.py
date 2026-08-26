import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.connection import get_db
from app.services.auth_service import ensure_seed_user

@pytest.mark.asyncio
async def test_api_key_lifecycle():
    db = await get_db()
    await ensure_seed_user(db)
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Login as Admin
        login_res = await ac.post("/api/v1/auth/login", json={"email": "admin@recovr.ai", "password": "Admin@123456"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create API Key
        create_res = await ac.post("/api/v1/api-keys", json={"name": "Production Test Key"}, headers=headers)
        assert create_res.status_code == 201
        key_data = create_res.json()
        assert "secret" in key_data
        assert key_data["secret"].startswith("sk_live_")
        key_id = key_data["id"]

        # 3. List API Keys (Secret must NOT be present)
        list_res = await ac.get("/api/v1/api-keys", headers=headers)
        assert list_res.status_code == 200
        keys = list_res.json()
        target_key = next((k for k in keys if k["id"] == key_id), None)
        assert target_key is not None
        assert "secret" not in target_key
        assert "masked_key" in target_key

        # 4. Revoke API Key
        revoke_res = await ac.post(f"/api/v1/api-keys/{key_id}/revoke", headers=headers)
        assert revoke_res.status_code == 200
        assert revoke_res.json()["status"] == "REVOKED"
