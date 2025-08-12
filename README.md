# ECC Health Pack (Azure Functions)

This adds four endpoints:
- GET /api/health
- GET /api/_audit/snapshot
- GET /api/_audit/env
- GET /api/metrics

## Install
1) Extract this ZIP.
2) In your repo, place these folders/files at the **root** (alongside your existing `host.json`):
   - Health/
   - AuditSnapshot/
   - AuditEnv/
   - Metrics/
   - .funcignore  (keep if you don't already have one)
   - host.json    (skip if you already have a host.json)
3) Commit & push to `main`.
4) Run your GitHub Action: **Deploy (Azure Functions — Publish Profile, auto-detect)**.
5) Run **Smoke Test (after Deploy)**.

If your app already has a `host.json`, keep your version. The functions work with the default route prefix `api`.
