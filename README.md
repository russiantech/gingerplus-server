# Southern Rose – Ginger Plus (Pursuing wellbeing)

Sales web app: storefront, ordering, Paystack payments, order tracking and a full admin.
`server/` FastAPI + PostgreSQL + Redis · `client/` React + TypeScript + Bootstrap (Vite).

## Run with Docker
```
cp server/.env.example server/.env   # edit SECRET_KEY, SMTP, Paystack keys
docker compose up --build            # site http://localhost:8080 · API docs http://localhost:8000/docs
```

## Run locally
```
# server
cd server && python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head          # creates tables; roles, products, content and the admin user are seeded on first start
uvicorn app.main:app --reload
pytest                        # 4 end-to-end tests (SQLite + fake Redis)

# client
cd client && npm install && npm run dev      # http://localhost:5173 (proxies /api to :8000)
```
Admin login: `admin@southernrose.ng` / `ChangeMe123!` (change via `FIRST_SUPERUSER_*` before first start, or in Admin → Users).

## Paystack
Set `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY`. Webhook URL: `https://<api-domain>/api/v1/payments/webhook/paystack`. Callback page: `<SITE_URL>/payment/callback`.
Without a key (non-production) a mock gateway lets you test the whole flow. Admins can verify or manually confirm any payment in Admin → Payments.

## Behaviour notes
- Registration is held in Redis until the emailed code is verified; only then is the user written to Postgres.
- Orders under 5 packs go to online payment; 5+ packs offer WhatsApp or full online checkout (`ONLINE_PAYMENT_MAX_PACKS`).
- Store matching is a suggestion; an admin approves, rejects or assigns manually.
- Roles/permissions are editable in Admin → Roles.

## Replace before launch
- Placeholder prices (₦18,000 / ₦9,000 per pack, 20+ pack tiers) – Admin → Products.
- Placeholder images in `client/public/images` – or upload per product/slide in the admin.
- Honey and Guarana ingredients and nutrition values were not in the brief – please supply them (Admin → Products).
- Social handles, address/map link, legal "last updated" dates – Admin → Settings / Pages.

See `client/ARCHITECTURE.md` for the front-end structure.
