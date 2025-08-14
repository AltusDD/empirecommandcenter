ECC – Canonical Labels (Backend)

Drop these into your Azure Functions repo (root level):
- shared/normalize.py
- PortfolioProperties/__init__.py
- PortfolioUnits/__init__.py
- PortfolioLeases/__init__.py
- PortfolioTenants/__init__.py
- PortfolioOwners/__init__.py

Then:
1) Commit & push to main
2) GitHub → Actions → Azure Functions deploy
3) Azure portal → Function App → Restart
4) Test: /api/portfolio/{properties|units|leases|tenants|owners}?limit=1