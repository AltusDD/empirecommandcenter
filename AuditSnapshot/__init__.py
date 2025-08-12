import azure.functions as func
import os, json, requests, re

def supa_count(base, key, resource):
    url = f"{base.rstrip('/')}/rest/v1/{resource}"
    try:
        r = requests.get(
            url,
            params={"select":"id","limit":"1","offset":"0"},
            headers={"apikey": key, "Authorization": f"Bearer {key}", "Prefer":"count=exact"},
            timeout=20
        )
        total = None
        cr = r.headers.get("Content-Range")  # e.g., "0-0/123"
        if cr and "/" in cr:
            try:
                total = int(cr.split("/")[-1])
            except Exception:
                total = None
        return {"status": r.status_code, "total": total, "snippet": r.text[:200]}
    except Exception as e:
        return {"error": str(e)}

def main(req: func.HttpRequest) -> func.HttpResponse:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    info = {
        "supabase_url_present": bool(supabase_url),
        "supabase_key_present": bool(supabase_key),
    }

    if not supabase_url or not supabase_key:
        body = {
            "ok": False,
            "reason": "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in Function App settings.",
            "how_to_fix": "Azure Portal → Function App → Configuration → Application settings → add both keys, Save & Restart.",
            "env": info
        }
        return func.HttpResponse(json.dumps(body), status_code=200, mimetype="application/json")

    result = {
        "ok": True,
        "env": info,
        "totals": {
            "properties": supa_count(supabase_url, supabase_key, "property_occupancy_v"),
            "units": supa_count(supabase_url, supabase_key, "units_v"),
            "leases": supa_count(supabase_url, supabase_key, "leases_enriched_v")
        }
    }
    return func.HttpResponse(json.dumps(result), status_code=200, mimetype="application/json")
