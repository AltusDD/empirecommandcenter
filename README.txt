
ECC Azure Hotfix: Ignore bad sort for Units/Tenants + safe sort for Leases

Copy the files over your backend repo:
- PortfolioUnits/__init__.py
- PortfolioTenants/__init__.py
- PortfolioLeases/__init__.py

Then commit, deploy via GitHub Actions (Azure Functions publish), and restart the Function App.
This guarantees Units and Tenants won't 400 due to unknown order-by columns.
