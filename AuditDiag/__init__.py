import azure.functions as func
import os, json, requests

def try_call(base, key, resource):
    if not base or not key:
        return {"skipped": True, "reason": "missing env"}
    url = f"{base.rstrip('/')}/rest/v1/{resource}"
    try:
        r = requests.get(url, params={"select":"*","limit":"1"},
                         headers={"apikey": key, "Authorization": f"Bearer {key}"}, timeout=15)
        body = r.text[:200]
        return {"status": r.status_code, "body_snippet": body}
    except Exception as e:
        return {"error": str(e)}

def main(req: func.HttpRequest) -> func.HttpResponse:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    diag = {
        "supabase_url_present": bool(supabase_url),
        "supabase_key_present": bool(supabase_key),
        "supabase_key_length": len(supabase_key or ""),
        "test_calls": {
            "property_occupancy_v": try_call(supabase_url, supabase_key, "property_occupancy_v"),
            "units_v": try_call(supabase_url, supabase_key, "units_v"),
            "leases_enriched_v": try_call(supabase_url, supabase_key, "leases_enriched_v")
        }
    }
    return func.HttpResponse(json.dumps(diag), status_code=200, mimetype="application/json")
