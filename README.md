# ECC Health Pack (Python, Azure Functions)

Adds four endpoints:
- GET /api/health
- GET /api/_audit/snapshot
- GET /api/_audit/env
- GET /api/metrics

## Install
1) Extract this ZIP.
2) Put everything at the **repo root** (same level as your existing `host.json`). If you already have a `host.json`, keep yours.
3) Commit & push to `main`.
4) Run **Deploy (Azure Functions — Publish Profile, auto-detect)** in GitHub Actions.

> This pack is for **Python** Function Apps.
