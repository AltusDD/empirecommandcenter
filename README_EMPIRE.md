# Empire Dropbox Integration — Ready Pack

## What this is
Azure Functions (Python) + Supabase schema to:
- Auto-provision Dropbox folders when a property/unit/lease is created in Supabase.
- Upload files into canonical folder structure and log to `file_assets` table.
- Fetch temporary download links for a stored asset id.

## Endpoints (function auth)
- POST /api/dropbox_provision_folders
- POST /api/upload
- GET  /api/get_temp_link?id=<asset_id>

## Azure App Settings (required)
- DROPBOX_APP_KEY
- DROPBOX_APP_SECRET
- DROPBOX_REFRESH_TOKEN   (use OAuth refresh token for long-lived auth)
- SUPABASE_URL            (https://<project>.supabase.co)
- SUPABASE_SERVICE_ROLE_KEY

## Deploy
Use your existing "Deploy (Azure Functions — Publish Profile, Build)" workflow.

## Supabase migration
Run: `db/001_init_supabase_empire.sql` (pre-filled with host: https://empirecommandcenter-altus.azurewebsites.net)

This migration:
- creates tables: file_assets, file_sync_audit
- enables extension: http
- installs triggers: on insert into properties, units, leases → calls /api/dropbox_provision_folders

## Quick tests
1) Azure → Configuration → add the five settings → Save & **Restart**
2) GET `/_audit/dropbox` (use the diagnostic function zip I provided) → should show your Dropbox account.
3) In Supabase, insert a test property/unit/lease → check Dropbox → folders created under `/Altus_Empire_Command_Center`
4) Upload:
   curl -X POST "https://empirecommandcenter-altus.azurewebsites.net/api/upload?code=<FUNCTION_KEY>"      -F "entity_type=PropertyPhoto"      -F 'meta={"property_id":1,"property_name":"Main Plaza"}'      -F "file=@test.jpg"
5) Supabase: select from `file_assets` and verify row; then
   GET `/api/get_temp_link?id=<id>` → returns a temporary URL.

Security note: endpoints use `authLevel:function`. Call them from server code or include the **function key** (`?code=<key>`) if you trigger from the browser (not recommended).
