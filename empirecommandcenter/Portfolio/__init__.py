import os, json, logging
import azure.functions as func
import httpx

# Prefer the repo's shared helpers if present (non-destructive import)
try:
    from shared.postgrest_utils import (
        build_paging_sort_search,
        parse_total_from_content_range,
        supabase_headers,
        cache_headers,
    )
    from shared.normalize import normalize_items
    HAVE_SHARED = True
except Exception as _imp_err:
    HAVE_SHARED = False

# Local fallbacks (only used if shared.* is not available)
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
def _to_int(val, default):
    try:
        return max(0, int(val))
    except Exception:
        return default
def _build_paging_sort_search(query_params, default_sort, allowed_sorts, search_columns):
    limit  = min(_to_int(query_params.get('limit'), DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE)
    offset = _to_int(query_params.get('offset'), 0)
    sort   = query_params.get('sort', default_sort)
    order  = query_params.get('order', 'asc').lower()
    if sort not in allowed_sorts:
        sort = default_sort
    if order not in ('asc','desc'):
        order = 'asc'
    search = (query_params.get('q') or '').strip()
    return {
        "limit": limit, "offset": offset, "sort": sort, "order": order,
        "search": search, "search_columns": search_columns,
        "meta": {"limit": limit, "offset": offset, "sort": sort, "order": order, "q": search}
    }
def _supabase_headers():
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    anon = os.getenv("SUPABASE_ANON_KEY", "")
    sr   = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    key  = sr or anon
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or key")
    return url, {"apikey": key, "Authorization": f"Bearer {key}"}
def _parse_total_from_content_range(h):
    # Example: items 0-49/1234  -> 1234
    if not h: return None
    try:
        parts = str(h).split("/")
        return int(parts[-1])
    except Exception:
        return None
def _cache_headers(seconds):
    try:
        s = max(0, int(seconds))
    except Exception:
        s = 0
    return {'Cache-Control': f'public, max-age={s}, s-maxage={s}, stale-while-revalidate={min(60,s)}'}
def _normalize_items(kind, items):
    return items

# Entities configuration
ENTITIES = {
    "properties": {
        "view": "property_occupancy_v",
        "default_sort": "property_name",
        "allowed_sorts": ["property_name","city","state","total_units","occupied_units","occupancy_rate","updated_at","created_at"],
        "search_columns": ["property_name","city","state","address1"],
        "cache": 300,
        "normalize_kind": "properties",
    },
    "units": {
        "view": "units_v",
        "default_sort": "unit_name",
        "allowed_sorts": ["unit_name","bedrooms","bathrooms","market_rent","status","updated_at","created_at"],
        "search_columns": ["unit_name","address1","city","state"],
        "cache": 120,
        "normalize_kind": "units",
    },
    "leases": {
        "view": "leases_v",
        "default_sort": "start_date",
        "allowed_sorts": ["start_date","end_date","rent","status","updated_at","created_at"],
        "search_columns": ["tenant_name","property_name","unit_name"],
        "cache": 60,
        "normalize_kind": "leases",
    },
    "tenants": {
        "view": "tenants_v",
        "default_sort": "tenant_name",
        "allowed_sorts": ["tenant_name","email","start_date","end_date","lease_status","updated_at","created_at"],
        "search_columns": ["tenant_name","email","property_name","unit_name"],
        "cache": 60,
        "normalize_kind": "tenants",
    },
    "owners": {
        "view": "owners_v",
        "default_sort": "owner_name",
        "allowed_sorts": ["owner_name","email","phone","updated_at","created_at"],
        "search_columns": ["owner_name","email"],
        "cache": 300,
        "normalize_kind": "owners",
    },
}

def _ok(body: dict, cache_seconds: int = 0) -> func.HttpResponse:
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    if HAVE_SHARED:
        try:
            headers.update(cache_headers(cache_seconds))
        except Exception:
            pass
    else:
        headers.update(_cache_headers(cache_seconds))
    return func.HttpResponse(json.dumps(body), status_code=200, headers=headers)

def _bad_request(msg: str) -> func.HttpResponse:
    return func.HttpResponse(json.dumps({"error": msg}), status_code=400, mimetype="application/json")

def _cors() -> func.HttpResponse:
    return func.HttpResponse(status_code=204, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        "Access-Control-Expose-Headers": "X-Total-Count"
    })

def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return _cors()

    entity = (req.route_params.get("entity") or "").lower().strip()
    if entity not in ENTITIES:
        return _bad_request(f"Unsupported entity '{entity}'")

    cfg = ENTITIES[entity]

    # Paging/sort/search
    if HAVE_SHARED:
        q = build_paging_sort_search(req.params, cfg["default_sort"], cfg["allowed_sorts"], cfg["search_columns"])
    else:
        q = _build_paging_sort_search(req.params, cfg["default_sort"], cfg["allowed_sorts"], cfg["search_columns"])
    meta = q["meta"]

    # Build Supabase REST URL
    if HAVE_SHARED:
        base_url, headers = None, None
        try:
            # supabase_headers() from shared returns (url, headers)
            base_url, headers = supabase_headers()
        except Exception as e:
            logging.exception("supabase_headers failed")
            return _bad_request("Supabase configuration missing")
    else:
        try:
            base_url, headers = _supabase_headers()
        except Exception:
            return _bad_request("Supabase configuration missing")

    view = cfg["view"]
    order = f"{q['sort']}.{q['order']}"
    rng_from = q["offset"]
    rng_to   = q["offset"] + q["limit"] - 1

    url = f"{base_url}/rest/v1/{view}"
    # Compose query params for PostgREST
    params = {
        "select": "*",
        "order": order,
    }
    # Range via headers
    range_header = {"Range": f"items={rng_from}-{rng_to}"}

    # Quick search across columns
    search = q["search"]
    if search:
        # Use ilike OR across columns: col.ilike.*value*
        # We'll AND them with OR using PostgREST syntax: or=(col.ilike.*v*,col2.ilike.*v*)
        ors = ",".join([f'{c}.ilike.*{search}*' for c in cfg["search_columns"]])
        params["or"] = f"({ors})"

    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(url, headers={**headers, **range_header}, params=params)
    except Exception as e:
        logging.exception("HTTP to Supabase failed")
        return func.HttpResponse(json.dumps({"error": "Upstream error"}), status_code=502, mimetype="application/json")

    # Handle upstream response
    if r.status_code // 100 != 2:
        return func.HttpResponse(r.text, status_code=r.status_code, mimetype="application/json")

    items = r.json() if r.text else []
    # Normalize if shared normalize_items is present
    if HAVE_SHARED:
        try:
            items = normalize_items(cfg["normalize_kind"], items)
        except Exception:
            pass

    total = None
    if HAVE_SHARED:
        total = parse_total_from_content_range(r.headers.get("Content-Range"))
    else:
        total = _parse_total_from_content_range(r.headers.get("Content-Range"))

    body = {"items": items, "total": total, **meta, "source": "azure_dynamic"}
    resp = _ok(body, cache_seconds=cfg["cache"])
    if total is not None:
        resp.headers["X-Total-Count"] = str(total)
    # CORS expose header
    resp.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp
