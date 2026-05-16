import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_full_auth_flow():
    # Naye HTTPX version ke mutabik transport use karna zaroori hai
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        
        # 1. Signup Test
        signup_payload = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "SecurePassword123"
        }
        signup_res = await ac.post("/signup", json=signup_payload)
        assert signup_res.status_code == 201

        # 2. Login Test
        login_payload = {
            "email": "testuser@example.com",
            "password": "SecurePassword123"
        }
        login_res = await ac.post("/login", json=login_payload)
        assert login_res.status_code == 200