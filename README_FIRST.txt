
==============================
EMPIRE MILESTONE — 2025-08-12
==============================

Purpose: This folder is a SAFE SNAPSHOT you can upload to GitHub under
milestones/2025-08-12 so we can always roll back.

KEEP THIS FOLDER. Do not modify the files inside after you upload them.

-------------------------------------------------
A) WHAT TALKS TO WHAT (plain English)
-------------------------------------------------
• Replit (the website you see) talks to: Azure Functions.
• Azure Functions (your backend) talks to: Supabase (database) and Dropbox.
• Supabase stores: your properties/units/leases and files table.
• Dropbox stores: the actual files; Supabase keeps the index of those files.

-------------------------------------------------
B) WHICH REPO WE USE (one repo)
-------------------------------------------------
Use this repo only: AltusDD/empirecommandcenter
(Stop putting code in other repos.)

-------------------------------------------------
C) EXACT FILES: WHERE THEY GO
-------------------------------------------------
1) Workflows (GitHub Actions) -> put these four files here:
   .github/workflows/deploy-azure-publishprofile.yml
   .github/workflows/smoke.yml
   .github/workflows/schema-sync-http.yml
   .github/workflows/schema-drift-strict-http.yml

2) Supabase SQL -> Do NOT put in production app. Keep them in repo at:
   supabase_sql/01_indexes.sql           (RUN in Supabase SQL editor)
   supabase_sql/02_rls_enable.sql        (RUN in Supabase SQL editor)
   supabase_sql/03_views_explicit.sql    (Optional, RUN after team sign-off)

3) Frontend helper prompts (for Replit Agent) -> just open the text files and paste:
   frontend_prompts/Prompt_A_API_Base.txt
   frontend_prompts/Prompt_B_Portfolio_Wire.txt
   frontend_prompts/Prompt_C_Theme_Unify.txt

4) Notes (for humans) — do nothing with these except read when needed:
   notes/azure_backend_notes.txt
   notes/dropbox_notes.txt

-------------------------------------------------
D) THE ORDER (click-by-click)
-------------------------------------------------
1) Upload the four workflows (see C.1).
2) In GitHub -> Actions:
   - Run: Deploy (Azure Functions — Publish Profile, Build)
   - Run: Smoke Test (after Deploy)
   - Run: Schema Sync (HTTP direct commit, safe)
   - Run: Schema Drift (Strict, HTTP safe)
3) Supabase -> SQL editor:
   - Paste and RUN 01_indexes.sql
   - Paste and RUN 02_rls_enable.sql
   - (Optional) After we confirm: RUN 03_views_explicit.sql
4) Replit Agent:
   - Open Prompt_A_API_Base.txt, copy, paste to the Agent, let it run.
   - Open Prompt_B_Portfolio_Wire.txt, copy, paste, let it run.
   - Open Prompt_C_Theme_Unify.txt, copy, paste, let it run.
5) Test in a browser:
   - Azure: /api/_audit/diag (should show 200 on three views)
   - Azure: /api/portfolio/properties?limit=5 (should show data)
   - Frontend: open Portfolio pages (tables load, no crash)
6) Dropbox (later, when ready):
   - Use notes/dropbox_notes.txt and the Dropbox Diag function I gave you earlier.

-------------------------------------------------
E) HOW TO MARK THE MILESTONE IN GITHUB (one time)
-------------------------------------------------
1) Create folder: milestones/2025-08-12 in the repo.
2) Drag this entire milestone folder into it (do not change names).
3) Commit to main with message: "chore: milestone 2025-08-12 snapshot"
4) Create a tag: v2.0-milestone-2025-08-12

Done. Rollback is easy: pick this tag in GitHub and revert.
