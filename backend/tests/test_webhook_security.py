import hmac
import hashlib
import json
import pytest
from httpx import AsyncClient, ASGITransport
from tests.conftest import get_admin_headers
from app.main import app
from app.config.settings import settings

@pytest.mark.asyncio
async def test_webhook_hmac_verification_and_idempotency():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=get_admin_headers()) as ac:
        # Create checkout and payment record first
        c_res = await ac.post("/api/v1/checkouts", json={"customer": {"name": "Webhook User", "email": "wh@test.com", "phone": "+123"}, "cart_value": 50.00})
        txn_id = c_res.json()["transaction_id"]
        p_res = await ac.post("/api/v1/payments/create", json={"transaction_id": txn_id, "payment_method": "card"})
        pay_id = p_res.json()["payment_id"]

        body_dict = {
            "event": "payment.failed",
            "event_id": f"evt_test_sec_{pay_id}",
            "payload": {
                "payment": {
                    "id": pay_id,
                    "amount": 5000,
                    "status": "failed",
                    "error_code": "GATEWAY_TIMEOUT",
                    "error_description": "Timeout"
                }
            }
        }
        body_bytes = json.dumps(body_dict).encode('utf-8')
        secret = settings.WEBHOOK_SECRET.encode('utf-8')
        valid_sig = hmac.new(secret, body_bytes, hashlib.sha256).hexdigest()

        # 1. Fire Webhook with valid signature
        wh_res1 = await ac.post(
            "/api/v1/webhooks/payment",
            content=body_bytes,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": valid_sig}
        )
        assert wh_res1.status_code == 200
        assert wh_res1.json()["received"] is True

        # 2. Fire duplicate event (Idempotency check)
        wh_res2 = await ac.post(
            "/api/v1/webhooks/payment",
            content=body_bytes,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": valid_sig}
        )
        assert wh_res2.status_code == 200
        assert wh_res2.json().get("idempotent") is True
