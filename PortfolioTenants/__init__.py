
import os, json, logging, requests, azure.functions as func
from shared.postgrest_utils import parse_total_from_content_range, supabase_headers, cache_headers

CACHE_SECONDS = 120

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        supabase_url = (os.getenv('SUPABASE_URL') or '').rstrip('/')
        if not supabase_url:
            return func.HttpResponse(json.dumps({"error":"SUPABASE_URL not configured"}), status_code=500, mimetype='application/json')

        base_url = f"{supabase_url}/rest/v1/tenants_list_v"

        # Ultra-safe: no sort/order; only paging + optional search
        qp = dict(req.params)

        try:
            limit = max(1, min(5000, int(qp.get("limit", "1000"))))
        except:
            limit = 1000
        try:
            if "offset" in qp:
                offset = max(0, int(qp.get("offset", "0")))
            else:
                page = max(1, int(qp.get("page", "1")))
                offset = (page - 1) * limit
        except:
            offset = 0

        params = {"limit": limit, "offset": offset}

        term = qp.get("search") or qp.get("q")
        if term:
            params["or"] = f"(tenant_name.ilike.*{term}*,email.ilike.*{term}*,property_name.ilike.*{term}*,unit_name.ilike.*{term}*)"

        headers = supabase_headers(req.headers.get('Authorization'))
        headers["Prefer"] = "count=exact"

        r = requests.get(base_url, headers=headers, params=params, timeout=30)

        if r.status_code not in (200,206):
            logging.error(f"Supabase Tenants failed: {r.status_code} {r.text}")
            return func.HttpResponse(r.text or json.dumps({"error":"Upstream error"}), status_code=r.status_code, mimetype='application/json')

        total = parse_total_from_content_range(r.headers.get('Content-Range'))
        body  = {"items": r.json() if r.text else [], "total": total, "limit": limit, "offset": offset, "source":"azure"}
        h = {'Content-Type':'application/json; charset=utf-8'}
        h.update(cache_headers(CACHE_SECONDS))
        return func.HttpResponse(json.dumps(body), status_code=200, headers=h)

    except Exception as e:
        logging.exception("PortfolioTenants ultra-safe failed")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype='application/json')
