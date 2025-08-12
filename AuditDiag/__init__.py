import azure.functions as func
import os, json, requests
def try_view(base, key, name):
    if not base or not key: return {"skipped": True}
    r = requests.get(f"{base.rstrip('/')}/rest/v1/{name}", params={"select":"id","limit":"1"},
                     headers={"apikey":key,"Authorization":f"Bearer {key}"}, timeout=15)
    return {"status": r.status_code, "content_range": r.headers.get("Content-Range")}
def main(req: func.HttpRequest) -> func.HttpResponse:
    b = os.getenv("SUPABASE_URL"); k = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    body = {"supabase_url_present": bool(b), "supabase_key_present": bool(k),
            "tests": {"property_occupancy_v": try_view(b,k,"property_occupancy_v"),
                      "units_v": try_view(b,k,"units_v"),
                      "leases_enriched_v": try_view(b,k,"leases_enriched_v")}}
    return func.HttpResponse(json.dumps(body), status_code=200, mimetype="application/json")
