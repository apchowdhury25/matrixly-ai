# Troubleshooting

## Chat widget not loading
1. Confirm the SupportForge API is running (health check `/v1/health`)
2. Check `data-api` and `data-key` on the embed script
3. Ensure your site origin is listed in CORS_ORIGINS
4. Hard-refresh the browser (Ctrl+F5)

## AI answers seem wrong
1. Re-index the knowledge base: `python -m src.cli seed`
2. Add or update files under `knowledge/`
3. Lower auto-resolve threshold in `config.yaml` so more replies require approval

## Email not ingesting
1. Set EMAIL_BACKEND=imap or gmail in `.env`
2. Verify credentials
3. Run `python scripts/ingest_email_once.py` for a one-shot poll

## Admin dashboard locked
Enter your SUPPORTFORGE_API_KEY when prompted. Keys are stored only in browser sessionStorage.
