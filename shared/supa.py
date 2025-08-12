import os, requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

def build_headers(extra=None):
    h = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Accept": "application/json"
    }
    if extra: h.update(extra)
    return h

def rest_get(name: str, params: dict):
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return {
            "ok": False,
            "status": 500,
            "error": "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY app setting"
        }
    url = f"{SUPABASE_URL}/rest/v1/{name}"
    qp = {"select": "*", **{k:v for k,v in params.items() if v is not None and v != ""}}
    try:
        r = requests.get(url, params=qp, headers=build_headers(), timeout=25)
        content_type = r.headers.get("Content-Type","")
        content_range = r.headers.get("Content-Range")
        # Try JSON first, keep snippet of raw text for debugging
        text_snippet = r.text[:800] if r.text else ""
        try:
            data = r.json()
        except Exception:
            data = None
        return {
            "ok": r.ok,
            "status": r.status_code,
            "url": url,
            "params": qp,
            "content_type": content_type,
            "content_range": content_range,
            "data": data,
            "text_snippet": text_snippet
        }
    except Exception as e:
        return {
            "ok": False,
            "status": 502,
            "error": str(e),
            "url": url,
            "params": qp
        }
