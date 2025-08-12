# Empire Deployment Pack — What to do

This adds **two** deployment workflows. Keep **one** and delete the other:

- `.github/workflows/deploy-azure-oidc.yml` (RECOMMENDED)
- `.github/workflows/deploy-azure-publishprofile.yml` (fallback)

## 1) Choose your path

### Option A — OIDC (recommended)
In GitHub repo **Settings → Secrets and variables → Actions**, add these **secrets**:
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

> These come from an Azure App Registration with a **federated credential** for this repo/branch.
> Portal: Azure AD → App registrations → (your app) → Certificates & secrets → **Federated credentials** → Add GitHub → select this repo → main.

Then push. The workflow `Deploy (Azure Functions — OIDC)` will log in and deploy to Function App: **empirecommandcenter-altus**.

### Option B — Publish profile (quick fix)
In GitHub secrets add:
- `AZUREAPPSERVICE_PUBLISHPROFILE` = the **full XML** from *Function App → Get publish profile* (use the correct slot if you have one).

Then push. The workflow `Deploy (Azure Functions — Publish Profile)` will deploy via Kudu.

## 2) Make sure the project is a Functions app
- `host.json` must be at the repository root **or** set `package:` to the functions subfolder in the workflow.
- Each function has `function.json` in its folder.

## 3) Run it
- Push to `main` or use **Actions → Run workflow**.
- Watch the logs. If it fails with 401 using publish profile, re-download a fresh profile and ensure **Basic auth** is enabled on the Kudu site.

---

_Generated 2025-08-12T14:52:19.543566Z_
