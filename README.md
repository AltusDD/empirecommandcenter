# ECC Portfolio API (Python, DEBUG)

Adds endpoints backed by Supabase views and returns **detailed error JSON** if the Supabase call fails:
- GET /api/portfolio/properties  -> property_occupancy_v
- GET /api/portfolio/units       -> units_v
- GET /api/portfolio/leases      -> leases_enriched_v
- GET /api/_audit/diag           -> connectivity checker

## Install
1) Extract ZIP.
2) Upload folders to repo root (same level as host.json). Commit to main.
3) Azure → Function App → Configuration → Application settings:
   - SUPABASE_URL = https://<your-project>.supabase.co
   - SUPABASE_SERVICE_ROLE_KEY = <service role key>
   Save & Restart.
4) Run Deploy workflow, then hit endpoints above.

If a portfolio endpoint returns 4xx/5xx, it includes a JSON body:
{ "status": 401, "url": ".../rest/v1/units_v", "text_snippet": "...", ... }
