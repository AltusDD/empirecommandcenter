import os, requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

def _headers(extra=None):
    h = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    if extra: h.update(extra)
    return h

def rest_get(name: str, params: dict):
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return None, 500, {"error": "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY app setting"}
    url = f"{SUPABASE_URL}/rest/v1/{name}"
    qp = {"select": "*", **{k:v for k,v in params.items() if v}}
    r = requests.get(url, params=qp, headers=_headers({"Accept":"application/json"}), timeout=20)
    try:
        data = r.json() if r.text else None
    except Exception:
        data = {"raw": r.text}
    return data, r.status_code, {"Content-Range": r.headers.get("Content-Range")}
