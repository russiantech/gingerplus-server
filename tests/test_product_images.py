import pytest

from tests.test_flow import API, admin_headers


async def _first_product(client, h):
    r = await client.get(f"{API}/admin/products", headers=h)
    return r.json()["items"][0]


async def test_patch_product_with_tiers_and_images_roundtrip(client):
    h = await admin_headers(client)
    p = await _first_product(client, h)
    variants = [{**v, "tiers": [{"min_qty": 20, "price": float(v["price"]) * 0.9, "label": "Wholesale"}]} for v in p["variants"]]
    r = await client.patch(f"{API}/admin/products/{p['id']}", headers=h, json={"images": ["/images/products/a.jpg", "/images/products/b.jpg"], "variants": variants})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["images"][0] == "/images/products/a.jpg" and body["variants"][0]["tiers"][0]["min_qty"] == 20
    # the public API sees the change straight away
    pub = (await client.get(f"{API}/catalog/products/{p['slug']}")).json()
    assert pub["images"][0] == "/images/products/a.jpg"
    # variant-level image can be set and cleared
    variants[0]["image_url"] = "/images/products/v.jpg"
    r = await client.patch(f"{API}/admin/products/{p['id']}", headers=h, json={"variants": variants})
    assert r.json()["variants"][0]["image_url"] == "/images/products/v.jpg"


async def test_errors_keep_cors_headers(client):
    r = await client.get(f"{API}/admin/products", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 401 and r.headers.get("access-control-allow-origin")
