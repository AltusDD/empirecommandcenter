# Empire ECC — CI/CD Pack

**What you get**
- Azure Functions deploy (publish profile, auto-detect `host.json`, remote build, `.funcignore`).
- Schema sync & drift check via HTTPS (no DB sockets).
- After-deploy smoke test hitting `/api/_audit/snapshot`, `/api/_audit/env`, `/metrics`.

**Setup (clicks)**
1) Upload the files in this ZIP to your repo root and commit to `main`.
2) Repo → Settings → Secrets and variables → Actions: add/update
   - `AZUREAPPSERVICE_PUBLISHPROFILE` → full XML from Azure “Get publish profile”
   - `SUPABASE_URL` → `https://<project>.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY` → service key
   - `APP_BASE_URL` → e.g. `https://empirecommandcenter-altus.azurewebsites.net`
3) Settings → Actions → General → **Workflow permissions** → Read and write.
4) Actions → run:
   - Schema Sync (HTTP direct commit, safe)
   - Schema Drift (Strict, HTTP safe)
   - Deploy (Azure Functions — Publish Profile, auto-detect)
   - Smoke Test (after Deploy)
