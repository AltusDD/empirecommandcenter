# Disabled Workflows (Altus Cleanup Patch)

These workflows were replaced with **disabled stubs** to stop accidental or duplicate deploys.

Disabled files:
- .github/workflows/deploy-altus.yml
- .github/workflows/deploy-azure-publishprofile.yml
- .github/workflows/deploy-fullrepo.yml
- .github/workflows/deploy-dropbox-function.yml
- .github/workflows/smoke.yml

They now only allow **manual** runs and do nothing except print an explanation.

## Why?
Your repo had multiple deploy pipelines pointing at different app names (including a non-existent one), which caused failed runs and confusion.

## How to re‑enable one later
1. Open the file you want to re-enable.
2. Replace the contents with the original from Git history (GitHub → History → find the prior revision).
   - Or, edit the stub and add the correct `on:` triggers and steps you need.
3. Commit to `main`.

For current staging deploys, use:
- .github/workflows/deploy-staging.yml  (active)
- .github/workflows/ai-smoke.yml        (active post-deploy smoke)

Make sure the staging environment has these secrets:
- AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID
- AZURE_FUNCTIONAPP_NAME = empirecommandcenter-altus-staging
- (Optional) FUNC_BASE_URL, FUNC_CODE_DEFAULT for the AI smoke
