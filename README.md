# ECC Portfolio API (Python, Azure Functions)

Adds these endpoints (anonymous GET):
- /api/portfolio/properties
- /api/portfolio/units
- /api/portfolio/leases
- /api/_audit/snapshot (uses Supabase counts if configured)

## Configure (once in Azure Portal → Function App → Configuration → Application settings)
- SUPABASE_URL = https://<your-project>.supabase.co
- SUPABASE_SERVICE_ROLE_KEY = <service role key>

## Deploy
1) Extract this ZIP at the repo root (same level as host.json).
2) Commit & push to main.
3) Run the "Deploy (Azure Functions — Publish Profile, auto-detect)" workflow.
4) Run "Smoke Test (after Deploy)".

Notes:
- Query params (limit, offset, order, filters) are passed through to Supabase REST.
- If the tables are named differently, tell me the correct names and I’ll adjust.
