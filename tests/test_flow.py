from unittest.mock import patch

API = "/api/v1"


async def admin_headers(client):
    r = await client.post(f"{API}/auth/login", json={"email": "admin@southernrose.ng", "password": "ChangeMe123!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['tokens']['access_token']}"}


async def test_registration_is_staged_in_redis_until_verified(client):
    with patch("app.services.auth_service.generate_numeric_code", return_value="123456"):
        r = await client.post(f"{API}/auth/register", json={"email": "Ada@Example.com", "password": "Passw0rdx", "first_name": "Ada"})
    assert r.status_code == 202
    # not persisted yet -> cannot log in
    assert (await client.post(f"{API}/auth/login", json={"email": "ada@example.com", "password": "Passw0rdx"})).status_code == 401
    bad = await client.post(f"{API}/auth/verify-email", json={"email": "ada@example.com", "code": "000000"})
    assert bad.status_code == 400
    ok = await client.post(f"{API}/auth/verify-email", json={"email": "ada@example.com", "code": "123456"})
    assert ok.status_code == 201 and ok.json()["user"]["email"] == "ada@example.com"
    assert (await client.post(f"{API}/auth/login", json={"email": "ada@example.com", "password": "Passw0rdx"})).status_code == 200


async def test_catalog_quote_checkout_and_payment(client):
    prods = (await client.get(f"{API}/catalog/products")).json()
    assert len(prods) == 3 and len(prods[0]["variants"]) == 2
    vid = prods[0]["variants"][0]["id"]
    q = (await client.post(f"{API}/checkout/quote", json={"items": [{"variant_id": vid, "quantity": 2}], "state": "Lagos"})).json()
    assert q["total"] == 2 * 18000 + 2500 and not q["is_wholesale"]
    big = (await client.post(f"{API}/checkout/quote", json={"items": [{"variant_id": vid, "quantity": 20}], "state": "Lagos"})).json()
    assert big["is_wholesale"] and big["lines"][0]["unit_price"] == 16500 and big["whatsapp_url"]

    body = {"items": [{"variant_id": vid, "quantity": 2}], "name": "Guest Buyer", "email": "guest@example.com", "phone": "08012345678",
            "address": {"recipient_name": "Guest Buyer", "phone": "08012345678", "line1": "1 Test St", "city": "Ikeja", "state": "Lagos"},
            "coupon_code": "welcome10", "request_store_match": True}
    r = await client.post(f"{API}/checkout", json=body)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["next_step"] == "pay_online" and data["authorization_url"]
    order = data["order"]
    assert order["discount_total"] == 3600 and order["total"] == 36000 - 3600 + 2500

    # tracking needs number + email
    assert (await client.post(f"{API}/orders/track", json={"number": order["number"], "email": "wrong@x.com"})).status_code == 404
    # mock gateway settles on verify
    v = (await client.get(f"{API}/payments/verify/{data['payment_reference']}")).json()
    assert v["status"] == "paid"
    t = (await client.post(f"{API}/orders/track", json={"number": order["number"], "email": "guest@example.com"})).json()
    assert t["payment_status"] == "paid" and t["status"] == "confirmed"

    h = await admin_headers(client)
    adm = (await client.get(f"{API}/admin/orders", headers=h)).json()
    assert adm["total"] == 1 and adm["items"][0]["assignment_status"] == "suggested"
    oid = adm["items"][0]["id"]
    ap = await client.post(f"{API}/admin/orders/{oid}/approve-store", headers=h)
    assert ap.status_code == 200 and ap.json()["assignment_status"] == "assigned"
    st = await client.post(f"{API}/admin/orders/{oid}/status", headers=h, json={"status": "dispatched", "note": "On the road"})
    assert st.status_code == 200
    dash = (await client.get(f"{API}/admin/dashboard", headers=h)).json()
    assert dash["kpis"]["revenue"] == 34900 and dash["kpis"]["orders"] == 1
    assert (await client.get(f"{API}/admin/payments", headers=h)).json()["total"] == 1


async def test_contact_inbox_direct_payment_and_permissions(client):
    r = await client.post(f"{API}/contact", json={"name": "Bar Owner", "email": "bar@example.com", "subject": "wholesale", "message": "Need 40 packs please"})
    assert r.status_code == 201
    assert (await client.get(f"{API}/admin/emails")).status_code == 401
    h = await admin_headers(client)
    mails = (await client.get(f"{API}/admin/emails", headers=h)).json()
    assert mails["total"] == 1 and mails["items"][0]["user_id"] is None
    d = await client.post(f"{API}/payments/direct", json={"name": "Bar Owner", "email": "bar@example.com", "amount": 50000})
    assert d.status_code == 201
    assert (await client.get(f"{API}/payments/verify/{d.json()['reference']}")).json()["status"] == "paid"
    # customer cannot reach admin
    with patch("app.services.auth_service.generate_numeric_code", return_value="111111"):
        await client.post(f"{API}/auth/register", json={"email": "c@example.com", "password": "Passw0rdx", "first_name": "C"})
    tok = (await client.post(f"{API}/auth/verify-email", json={"email": "c@example.com", "code": "111111"})).json()["tokens"]["access_token"]
    assert (await client.get(f"{API}/admin/orders", headers={"Authorization": f"Bearer {tok}"})).status_code == 403


async def test_public_content(client):
    b = (await client.get(f"{API}/content/bootstrap")).json()
    assert len(b["hero"]) == 3 and b["settings"]["brand"]["slogan"] == "Pursuing wellbeing"
    assert (await client.get(f"{API}/content/pages/about-us")).status_code == 200
    assert len((await client.get(f"{API}/content/faqs")).json()) == 17
    n = (await client.get(f"{API}/stores/nearest", params={"state": "Lagos"})).json()
    assert n["store"]["name"] == "Southern Rose HQ"
