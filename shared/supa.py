import os, requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
ECC_DEBUG = os.getenv("ECC_DEBUG", "false").lower() in ("1","true","yes")
ECC_CACHE_SECONDS = int(os.getenv("ECC_CACHE_SECONDS", "60"))

def headers(extra=None):
    h = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Accept": "application/json"
    }
    if extra: h.update(extra)
    return h

def rest_get(view: str, params: dict):
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return {"ok": False, "status": 500, "error": "missing_supabase_env"}
    url = f"{SUPABASE_URL}/rest/v1/{view}"
    qp = {"select": "*", **{k:v for k,v in params.items() if v not in (None,"")}}
    try:
        r = requests.get(url, params=qp, headers=headers(), timeout=25)
        try:
            data = r.json()
        except Exception:
            data = None
        res = {"ok": r.ok, "status": r.status_code, "data": data}
        if ECC_DEBUG:
            res.update({
                "url": url, "params": qp,
                "content_type": r.headers.get("Content-Type"),
                "content_range": r.headers.get("Content-Range"),
                "text_snippet": r.text[:800],
            })
        return res
    except Exception as e:
        res = {"ok": False, "status": 502, "error": str(e)}
        if ECC_DEBUG:
            res.update({"url": url, "params": qp})
        return res
