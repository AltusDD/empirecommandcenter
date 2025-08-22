# ECC Dynamic Portfolio Patch (Non‑Destructive)

This patch adds **one** dynamic Azure Function:
- Route: `/api/portfolio/{entity}` where `{entity}` ∈ {properties, units, leases, tenants, owners}
- Files added:
  - `empirecommandcenter/Portfolio/function.json`
  - `empirecommandcenter/Portfolio/__init__.py`

## Why this is safe
- No existing folders/files are modified.
- Uses your repo’s `shared.postgrest_utils` and `shared.normalize` **if present**; otherwise falls back to tiny local adapters.
- Leaves `host.json`, workflows, and existing `Portfolio*` function folders unchanged.

## How to apply
1. Copy the `empirecommandcenter/Portfolio/` folder into the **root of your Function App** (same level as `host.json`).
2. Ensure the Function App has these Application Settings set:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY` (or `SUPABASE_SERVICE_ROLE_KEY`)
3. Deploy using your existing GitHub Action (OIDC) or ZipDeploy.
4. Smoke test:
   ```bash
   BASE="https://<YOUR_FUNC_APP>.azurewebsites.net/api"
   curl -s "$BASE/portfolio/properties?limit=3" | jq .
   curl -s "$BASE/portfolio/units?limit=3" | jq .
   ```

## Notes
- Sorting & search:
  - `?limit=50&offset=0&sort=property_name&order=asc&q=gary`
- Sets `X-Total-Count` when upstream includes `Content-Range`.
- Sends conservative CORS headers on this route only.
