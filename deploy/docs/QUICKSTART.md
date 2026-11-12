# Quick Start

```bash
source /home/gingerpl/virtualenv/api.gingerplus.ng/3.11/bin/activate && cd /home/gingerpl/api.gingerplus.ng
bash deploy/deploy.sh          # one time
bash deploy/control.sh status
bash deploy/control.sh logs
bash deploy/control.sh restart # after code/.env change
bash deploy/control.sh health
```

## Update the API
```bash
cd ~/api.gingerplus.ng && git pull origin main      # or upload the changed files
pip install -r requirements.txt && alembic upgrade head
bash deploy/control.sh restart
```

## Update the storefront
Rebuild locally (`npm run build` in `client/`) and replace the contents of `public_html/` with `dist/`.

## Troubleshooting
| Problem | Fix |
|---------|-----|
| 404/503 on api.gingerplus.ng | `control.sh status`; check `.htaccess` port = `PORT`; `control.sh logs-err` |
| "Supervisor stuck" | `control.sh kill && sleep 2 && control.sh start` |
| Storefront loads but no products | `CORS_ORIGINS` missing the storefront origin, or storefront built without `VITE_API_URL` |
| Refreshing a page gives 404 | storefront `.htaccess` missing from `public_html` |
| After reboot | wait ~30s (cron `@reboot`), then `control.sh status` |
