# Pre-Flight Checklist

## cPanel
- [ ] Subdomain `api.gingerplus.ng` created; SSL (AutoSSL) active on `api.` and `gingerplus.ng`
- [ ] Python App created: **3.11**, app root `api.gingerplus.ng` (virtualenv exists)
- [ ] PostgreSQL database + user created and linked
- [ ] SSH access enabled

```bash
ls ~/virtualenv/api.gingerplus.ng/3.11/bin/activate
ls ~/api.gingerplus.ng/index.py ~/api.gingerplus.ng/.env
```

## Config
- [ ] `deploy/config.env`: `CPANEL_USER="gingerpl"`, `DOMAIN="api.gingerplus.ng"`, `PYTHON_VERSION="3.11"`, unique `PORT`
- [ ] `.env` filled (see ENV_VARIABLES_GUIDE.md), `chmod 600 .env`
- [ ] `pip install -r requirements.txt` finished without errors
- [ ] `alembic upgrade head` OK; `python -m app.db.init_db` run once

## Manual run test (before Supervisor)
```bash
source ~/virtualenv/api.gingerplus.ng/3.11/bin/activate && cd ~/api.gingerplus.ng
uvicorn index:app --host 127.0.0.1 --port 8001      # Ctrl+C after: curl localhost:8001/health
```

## Go live
- [ ] `bash deploy/deploy.sh` → RUNNING
- [ ] `.htaccess` proxy to the PORT in place; `https://api.gingerplus.ng/health` returns ok
- [ ] Storefront `dist/` (with `.htaccess`) uploaded to `public_html`; `https://gingerplus.ng` loads and shows products
- [ ] Login to admin, set Paystack keys, make a test payment, check the email inbox
- [ ] Cron: `*/5 * * * * bash ~/api.gingerplus.ng/deploy/monitor.sh`
