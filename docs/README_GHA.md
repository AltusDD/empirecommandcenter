# Nightly DB Audit — GitHub Actions

This workflow runs the Supabase audit nightly and prints the results into the workflow summary.
Optionally, you can extend it to update `/docs/STATUS.md` in a later step.

## How to install
1) In repo **AltusDD/empirecommandcenter** (Azure Functions backend), create folder `.github/workflows/` if it doesn't exist.
2) Put `nightly-db-audit.yml` into that folder.
3) In GitHub → Settings → Secrets → Actions, add:
   - `SUPABASE_DB_URL` — full Postgres connection string for your Supabase DB (service role or read-only role).
4) In GitHub → Actions → select **Nightly — DB Audit** → **Run workflow** to test manually.
