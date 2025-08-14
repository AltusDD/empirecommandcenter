import os, json, logging, requests, azure.functions as func
from shared.postgrest_utils import build_paging_sort_search, parse_total_from_content_range, supabase_headers, cache_headers
from shared.normalize import normalize_items

ALLOWED_SORTS   = ["owner_name", "properties_count", "units_count", "occupied_units", "occupancy_rate", "updated_at", "created_at"]
SEARCH_COLUMNS  = ["owner_name"]
DEFAULT_SORT    = "owner_name"
CACHE_SECONDS   = 120
VIEW_NAME       = "owners_summary_v"

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        supabase_url = (os.getenv('SUPABASE_URL') or '').rstrip('/')
        if not supabase_url:
            logging.error("SUPABASE_URL not configured")
            return func.HttpResponse(json.dumps({"error":"SUPABASE_URL not configured"}), status_code=500, mimetype='application/json')

        base_url = f"{supabase_url}/rest/v1/{VIEW_NAME}"
        params, meta = build_paging_sort_search(req.params, default_sort=DEFAULT_SORT, allowed_sorts=ALLOWED_SORTS, search_columns=SEARCH_COLUMNS)
        headers = supabase_headers(req.headers.get('Authorization'))

        r = requests.get(base_url, headers=headers, params=params, timeout=30)

        if r.status_code not in (200, 206):
            logging.error(f"Supabase request failed: {r.status_code} {r.text[:300]}")
            return func.HttpResponse(r.text, status_code=r.status_code, mimetype='application/json')

        total = parse_total_from_content_range(r.headers.get('Content-Range'))
        items = r.json() if r.text else []
        items = normalize_items("owners", items)

        body  = {"items": items, "total": total, **meta, "source":"azure"}
        h = {'Content-Type':'application/json; charset=utf-8'}
        h.update(cache_headers(CACHE_SECONDS))
        return func.HttpResponse(json.dumps(body), status_code=200, headers=h)

    except Exception as e:
        logging.exception("/portfolio/owners failed")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype='application/json')