
import os, json, logging, requests, azure.functions as func
from shared.postgrest_utils import build_paging_sort_search, parse_total_from_content_range, supabase_headers, cache_headers

ALLOWED_SORTS   = ['property_name', 'city', 'state', 'total_units', 'occupied_units', 'occupancy_rate', 'updated_at', 'created_at']
SEARCH_COLUMNS  = ['property_name', 'city', 'state']
DEFAULT_SORT    = "property_name"
CACHE_SECONDS   = 300

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        supabase_url = (os.getenv('SUPABASE_URL') or '').rstrip('/')
        if not supabase_url:
            return func.HttpResponse(json.dumps({"error":"SUPABASE_URL not configured"}), status_code=500, mimetype='application/json')

        base_url = f"{supabase_url}/rest/v1/property_occupancy_v"
        params, meta = build_paging_sort_search(req.params, default_sort=DEFAULT_SORT, allowed_sorts=ALLOWED_SORTS, search_columns=SEARCH_COLUMNS)
        headers = supabase_headers(req.headers.get('Authorization'))

        r = requests.get(base_url, headers=headers, params=params, timeout=30)

        if r.status_code not in (200, 206):
            logging.error(f"Supabase request failed: {r.status_code} {r.text}")
            return func.HttpResponse(r.text or json.dumps({"error":"Upstream error"}), status_code=r.status_code, mimetype='application/json')

        total = parse_total_from_content_range(r.headers.get('Content-Range'))
        body  = {"items": r.json() if r.text else [], "total": total, **meta, "source":"azure"}
        headers_out = {'Content-Type':'application/json; charset=utf-8'}
        headers_out.update(cache_headers(CACHE_SECONDS))
        return func.HttpResponse(json.dumps(body), status_code=200, headers=headers_out)

    except Exception as e:
        logging.exception("Function failed")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype='application/json')
