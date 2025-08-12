# ECC Portfolio API (Python) — Production
- GET /api/portfolio/properties  -> property_occupancy_v
- GET /api/portfolio/units       -> units_v
- GET /api/portfolio/leases      -> leases_enriched_v
- GET /api/_audit/diag           -> quick connectivity test

## App settings (Azure → Function App → Configuration)
- SUPABASE_URL = https://<your-project>.supabase.co
- SUPABASE_SERVICE_ROLE_KEY = <service role key>
- ECC_CACHE_SECONDS = 60       # optional
- ECC_DEBUG = false            # set true to include helpful debug fields in errors

Deploy with Oryx build enabled so requirements are installed.
