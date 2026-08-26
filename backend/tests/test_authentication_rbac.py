import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.connection import get_db
from app.services.auth_service import ensure_seed_user

@pytest.mark.asyncio
async def test_auth_login_success_and_me():
    db = await get_db()
    await ensure_seed_user(db)
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Login with seed admin credentials
        login_res = await ac.post("/api/v1/auth/login", json={"email": "admin@recovr.ai", "password": "Admin@123456"})
        assert login_res.status_code == 200
        data = login_res.json()
        assert "access_token" in data
        token = data["access_token"]
        assert data["user"]["email"] == "admin@recovr.ai"

        # Verify /auth/me with bearer token
        me_res = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "admin@recovr.ai"

@pytest.mark.asyncio
async def test_auth_login_invalid_credentials():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/v1/auth/login", json={"email": "admin@recovr.ai", "password": "WrongPassword123"})
        assert res.status_code == 401

@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/api-keys")
        assert res.status_code == 401
