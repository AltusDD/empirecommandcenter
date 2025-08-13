import os
import json
import logging
import requests
import azure.functions as func
from shared.postgrest_utils import (
    build_paging_sort_search,
    parse_total_from_content_range,
    supabase_headers,
    cache_headers,
)

ALLOWED_SORTS = [
    'tenant_name', 'email', 'property_name', 'unit_name',
    'lease_start', 'lease_end', 'lease_status', 'updated_at', 'created_at'
]
SEARCH_COLUMNS = ['tenant_name', 'email', 'property_name', 'unit_name']
DEFAULT_SORT = 'tenant_name'
CACHE_SECONDS = 120

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        supabase_url = (os.getenv('SUPABASE_URL') or '').rstrip('/')
        if not supabase_url:
            return func.HttpResponse(
                json.dumps({"error": "SUPABASE_URL not configured"}),
                status_code=500, mimetype='application/json')

        base_url = f"{supabase_url}/rest/v1/tenants_list_v"
        params, meta = build_paging_sort_search(req.params,
                                                default_sort=DEFAULT_SORT,
                                                allowed_sorts=ALLOWED_SORTS,
                                                search_columns=SEARCH_COLUMNS)

        headers = supabase_headers(req.headers.get('Authorization'))
        r = requests.get(base_url, headers=headers, params=params, timeout=30)

        if r.status_code not in (200, 206):
            return func.HttpResponse(r.text, status_code=r.status_code,
                                     mimetype='application/json')

        total = parse_total_from_content_range(r.headers.get('Content-Range'))
        body = {
            'items': r.json() if r.text else [],
            'total': total,
            **meta,
            'source': 'azure'
        }
        resp_headers = {'Content-Type': 'application/json; charset=utf-8'}
        resp_headers.update(cache_headers(CACHE_SECONDS))
        return func.HttpResponse(json.dumps(body), status_code=200, headers=resp_headers)

    except Exception as e:
        logging.exception("/portfolio/tenants failed")
        return func.HttpResponse(
            json.dumps({"error": str(e)}), status_code=500, mimetype='application/json')
