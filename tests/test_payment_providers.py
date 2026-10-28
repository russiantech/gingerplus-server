"""Provider credentials (encrypted, admin-managed, env fallback) + the backend-mediated in-app payment flow."""
import hashlib
import hmac
import json

import httpx
import pytest
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from tests.test_flow import API, admin_headers

REQUESTS: list[httpx.Request] = []
STATE = {"paystack_status": "success", "paystack_amount": None, "fw_status": "successful"}


def handler(request: httpx.Request) -> httpx.Response:
    REQUESTS.append(request)
    path = request.url.path
    if request.url.host == "api.paystack.co":
        if path == "/transaction/initialize":
            body = json.loads(request.content)
            return httpx.Response(200, json={"status": True, "data": {"authorization_url": "https://checkout.paystack.com/abc", "access_code": "AC_123", "reference": body["reference"]}})
        if path.startswith("/transaction/verify/"):
            ref = path.rsplit("/", 1)[1]
            amount = STATE["paystack_amount"] or int(PAID[ref] * 100)
            return httpx.Response(200, json={"status": True, "data": {"status": STATE["paystack_status"], "amount": amount, "currency": "NGN", "channel": "card", "gateway_response": "Successful", "reference": ref}})
        if path == "/transaction":
            return httpx.Response(200, json={"status": True, "data": []})
    if request.url.host == "api.flutterwave.com":
        if path == "/v3/payments":
            return httpx.Response(200, json={"status": "success", "data": {"link": "https://checkout.flutterwave.com/pay/xyz"}})
        if path == "/v3/transactions/verify_by_reference":
            ref = request.url.params["tx_ref"]
            return httpx.Response(200, json={"status": "success", "data": {"status": STATE["fw_status"], "amount": PAID[ref], "currency": "NGN", "payment_type": "card", "tx_ref": ref}})
        if path == "/v3/banks/NG":
            return httpx.Response(200, json={"status": "success", "data": []})
    return httpx.Response(401, json={"status": False, "message": "Invalid key"})


PAID: dict[str, float] = {}
_real = httpx.AsyncClient


@pytest.fixture(autouse=True)
def fake_gateways(monkeypatch):
    REQUESTS.clear()
    PAID.clear()
    STATE.update(paystack_status="success", paystack_amount=None, fw_status="successful")

    def factory(*a, **kw):
        kw["transport"] = httpx.MockTransport(handler)
        return _real(*a, **kw)
    for mod in ("paystack", "flutterwave"):
        monkeypatch.setattr(f"app.services.gateways.{mod}.httpx.AsyncClient", factory)
    monkeypatch.setattr(settings, "PAYSTACK_SECRET_KEY", "")
    monkeypatch.setattr(settings, "FLUTTERWAVE_SECRET_KEY", "")


async def save_paystack(client, h, **over):
    body = {"is_enabled": True, "mode": "test", "public_key": "pk_test_dbpublic", "secret_key": "sk_test_dbsecret1234", **over}
    r = await client.put(f"{API}/admin/payment-providers/paystack", headers=h, json=body)
    assert r.status_code == 200, r.text
    return r.json()


async def one_pack_order(client, method="paystack"):
    prods = (await client.get(f"{API}/catalog/products")).json()
    vid = prods[0]["variants"][0]["id"]
    body = {"items": [{"variant_id": vid, "quantity": 1}], "name": "Guest Buyer", "email": "guest@example.com", "phone": "08012345678",
            "address": {"recipient_name": "Guest Buyer", "phone": "08012345678", "line1": "1 Test St", "city": "Ikeja", "state": "Lagos"}, "payment_method": method}
    r = await client.post(f"{API}/checkout", json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def test_secrets_are_encrypted_at_rest_and_never_returned(client):
    h = await admin_headers(client)
    out = await save_paystack(client, h)
    assert out["has_secret"] and out["source"] == "database" and out["secret_masked"].endswith("1234") and "dbsecret" not in json.dumps(out)
    listing = json.dumps((await client.get(f"{API}/admin/payment-providers", headers=h)).json())
    assert "sk_test_dbsecret1234" not in listing
    async with engine.connect() as conn:
        raw = (await conn.execute(text("select secret_key_enc, secret_fingerprint from payment_providers where provider='paystack'"))).one()
    assert raw[0].startswith("enc1:") and "dbsecret" not in raw[0] and raw[1] == hashlib.sha256(b"sk_test_dbsecret1234").hexdigest()[:16]
    # blank secret on update keeps the stored one
    again = await save_paystack(client, h, secret_key="", mode="live")
    assert again["has_secret"] and again["mode"] == "live" and again["secret_fingerprint"] == raw[1]


async def test_only_settings_managers_can_manage_providers(client):
    assert (await client.get(f"{API}/admin/payment-providers")).status_code == 401
    await client.post(f"{API}/auth/register", json={"email": "c@example.com", "password": "Passw0rdx", "first_name": "C"})
    from unittest.mock import patch
    with patch("app.services.auth_service.generate_numeric_code", return_value="123456"):
        await client.post(f"{API}/auth/register", json={"email": "c2@example.com", "password": "Passw0rdx", "first_name": "C"})
    tok = (await client.post(f"{API}/auth/verify-email", json={"email": "c2@example.com", "code": "123456"})).json()["tokens"]["access_token"]
    assert (await client.get(f"{API}/admin/payment-providers", headers={"Authorization": f"Bearer {tok}"})).status_code == 403


async def test_database_credentials_drive_the_full_in_app_flow(client):
    h = await admin_headers(client)
    await save_paystack(client, h)
    data = await one_pack_order(client)
    pay = data["payment"]
    # backend → Paystack used the admin-saved key; browser gets only the access code + public key
    init_req = next(r for r in REQUESTS if r.url.path == "/transaction/initialize")
    assert init_req.headers["authorization"] == "Bearer sk_test_dbsecret1234"
    assert pay["provider"] == "paystack" and pay["access_code"] == "AC_123" and pay["public_key"] == "pk_test_dbpublic" and not pay["mock"]
    assert "sk_test" not in json.dumps(data)
    PAID[pay["reference"]] = pay["amount"]
    v = (await client.post(f"{API}/payments/verify", json={"reference": pay["reference"]})).json()
    assert v["status"] == "paid" and v["order_number"] == data["order"]["number"]
    # idempotent
    assert (await client.post(f"{API}/payments/verify", json={"reference": pay["reference"]})).json()["status"] == "paid"
    cfg = (await client.get(f"{API}/payments/config")).json()
    assert cfg["online"] == {"available": True, "provider": "paystack", "mock": False}


async def test_environment_fallback_when_nothing_saved(client, monkeypatch):
    monkeypatch.setattr(settings, "PAYSTACK_SECRET_KEY", "sk_test_envkey")
    data = await one_pack_order(client)
    assert next(r for r in REQUESTS if r.url.path == "/transaction/initialize").headers["authorization"] == "Bearer sk_test_envkey"
    h = await admin_headers(client)
    listing = {i["provider"]: i for i in (await client.get(f"{API}/admin/payment-providers", headers=h)).json()}
    assert listing["paystack"]["source"] == "environment" and listing["paystack"]["env_available"] and data["payment"]["provider"] == "paystack"
    # saving DB credentials takes precedence; deleting them falls back again
    await save_paystack(client, h)
    REQUESTS.clear(); await one_pack_order(client)
    assert next(r for r in REQUESTS if r.url.path == "/transaction/initialize").headers["authorization"] == "Bearer sk_test_dbsecret1234"
    assert (await client.delete(f"{API}/admin/payment-providers/paystack", headers=h)).status_code == 200
    REQUESTS.clear(); await one_pack_order(client)
    assert next(r for r in REQUESTS if r.url.path == "/transaction/initialize").headers["authorization"] == "Bearer sk_test_envkey"


async def test_webhook_uses_the_credentials_in_use(client):
    h = await admin_headers(client)
    await save_paystack(client, h)
    data = await one_pack_order(client)
    ref = data["payment"]["reference"]; PAID[ref] = data["payment"]["amount"]
    body = json.dumps({"event": "charge.success", "data": {"reference": ref, "status": "success", "amount": int(data["payment"]["amount"] * 100), "currency": "NGN", "channel": "card"}}).encode()
    bad = await client.post(f"{API}/payments/webhook/paystack", content=body, headers={"x-paystack-signature": "nope"})
    assert bad.status_code == 401
    sig = hmac.new(b"sk_test_dbsecret1234", body, hashlib.sha512).hexdigest()
    ok = await client.post(f"{API}/payments/webhook/paystack", content=body, headers={"x-paystack-signature": sig})
    assert ok.status_code == 200
    assert (await client.get(f"{API}/payments/verify/{ref}")).json()["status"] == "paid"
    # a signature made with an old/other key is rejected
    other = hmac.new(b"sk_test_other", body, hashlib.sha512).hexdigest()
    assert (await client.post(f"{API}/payments/webhook/paystack", content=body, headers={"x-paystack-signature": other})).status_code == 401


async def test_amount_mismatch_is_rejected(client):
    h = await admin_headers(client)
    await save_paystack(client, h)
    data = await one_pack_order(client)
    STATE["paystack_amount"] = 100  # ₦1 instead of the order total
    r = await client.post(f"{API}/payments/verify", json={"reference": data["payment"]["reference"]})
    assert r.status_code == 402 and r.json()["code"] == "amount_mismatch"


async def test_disabled_provider_is_off_and_test_connection(client):
    h = await admin_headers(client)
    await save_paystack(client, h)
    t = (await client.post(f"{API}/admin/payment-providers/paystack/test", headers=h)).json()
    assert t["ok"] and t["source"] == "database"
    await client.put(f"{API}/admin/payment-providers/paystack", headers=h, json={"is_enabled": False})
    data = await one_pack_order(client)
    assert data["payment"]["provider"] == "mock"  # dev mock; in production this would be "unavailable"
    assert (await client.post(f"{API}/admin/payment-providers/flutterwave/test", headers=h)).json()["ok"] is False
    bad = await client.put(f"{API}/admin/payment-providers/flutterwave", headers=h, json={"is_enabled": True})
    assert bad.status_code == 400  # cannot enable without a key


async def test_flutterwave_default_provider_flow(client):
    h = await admin_headers(client)
    await save_paystack(client, h)
    r = await client.put(f"{API}/admin/payment-providers/flutterwave", headers=h, json={"is_enabled": True, "public_key": "FLWPUBK_TEST-x", "secret_key": "FLWSECK_TEST-secret", "webhook_secret": "hash123"})
    assert r.status_code == 200 and r.json()["has_webhook_secret"]
    assert (await client.post(f"{API}/admin/payment-providers/flutterwave/default", headers=h)).json()["is_default"]
    data = await one_pack_order(client)
    pay = data["payment"]
    assert pay["provider"] == "flutterwave" and pay["public_key"] == "FLWPUBK_TEST-x" and pay["access_code"] == pay["reference"]
    PAID[pay["reference"]] = pay["amount"]
    assert (await client.post(f"{API}/payments/verify", json={"reference": pay["reference"]})).json()["status"] == "paid"
    # webhook auth uses the saved verif-hash
    assert (await client.post(f"{API}/payments/webhook/flutterwave", json={"event": "charge.completed", "data": {}}, headers={"verif-hash": "wrong"})).status_code == 401
    assert (await client.post(f"{API}/payments/webhook/flutterwave", json={"event": "charge.completed", "data": {}}, headers={"verif-hash": "hash123"})).status_code == 200


async def test_bank_transfer_details_are_public_when_enabled(client):
    h = await admin_headers(client)
    assert (await client.get(f"{API}/payments/config")).json()["bank_transfer"] is None
    r = await client.put(f"{API}/admin/payment-providers/bank_transfer", headers=h, json={"is_enabled": True, "extra": {"bank_name": "GTBank", "account_name": "Southern Rose Ltd", "account_number": "0123456789", "junk": "x"}})
    assert r.status_code == 200 and "junk" not in r.json()["extra"]
    bt = (await client.get(f"{API}/payments/config")).json()["bank_transfer"]
    assert bt["bank_name"] == "GTBank" and bt["account_number"] == "0123456789"


async def test_mock_gateway_is_unavailable_in_production(client, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    cfg = (await client.get(f"{API}/payments/config")).json()
    assert cfg["online"]["available"] is False
    data = await one_pack_order(client)
    assert data["next_step"] == "retry_payment" and data["payment"] is None
    assert (await client.post(f"{API}/payments/mock/complete", json={"reference": "x", "outcome": "success"})).status_code == 404
