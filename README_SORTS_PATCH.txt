
ECC Backend Sorts Patch

Copy these files over your existing function folders in the Function App repo:
- PortfolioLeases/__init__.py
- PortfolioUnits/__init__.py
- PortfolioTenants/__init__.py

Then commit, deploy via the Azure Functions workflow, and restart the app.
This patch prevents HTTP 400 due to invalid order-by columns by sanitizing/mapping sorts
to columns known to exist in the Supabase views.
