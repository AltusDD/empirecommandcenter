
ECC Portfolio Core Restore (Properties / Units / Leases)

What this contains
------------------
Three Azure Function folders ready to drop into your Function App repo ROOT (same level as host.json):

  PortfolioProperties/  -> GET /api/portfolio/properties
  PortfolioUnits/       -> GET /api/portfolio/units
  PortfolioLeases/      -> GET /api/portfolio/leases

Each function:
  • Proxies to the Supabase PostgREST view (see names in __init__.py)
  • Accepts paging, sort, search via build_paging_sort_search()
  • Returns { items, total, ...meta, source:"azure" } with cache headers
  • Uses $return output binding (no 'res' param)


Install (copy/paste level)
--------------------------
1) Download this zip and extract into the backend repo ROOT (AltusDD/empirecommandcenter).
   After extraction you should see folders at the top level:
     /PortfolioProperties/
     /PortfolioUnits/
     /PortfolioLeases/
     /shared/ (already exists)
     host.json

2) Commit and push to main.

3) GitHub → Actions → Run "Azure Functions — Publish Profile, Build".

4) Azure Portal → Function App → Restart.

5) Verify (expect 401/403 if not logged in):
   https://empirecommandcenter-altus.azurewebsites.net/api/portfolio/properties?limit=1
   https://empirecommandcenter-altus.azurewebsites.net/api/portfolio/units?limit=1
   https://empirecommandcenter-altus.azurewebsites.net/api/portfolio/leases?limit=1

6) Refresh the Replit app. 404s on properties/units/leases should be gone.
