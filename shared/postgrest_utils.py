
import os
from urllib.parse import quote

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

def _to_int(val, default):
    try:
        return max(0, int(val))
    except Exception:
        return default

def build_paging_sort_search(query_params, *, default_sort: str, allowed_sorts: list, search_columns: list):
    limit  = min(_to_int(query_params.get('limit'), DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE)
    offset = _to_int(query_params.get('offset'), 0)
    sort  = query_params.get('sort', default_sort)
    order = query_params.get('order', 'asc').lower()
    order = 'desc' if order == 'desc' else 'asc'
    sort_cols   = [c.strip() for c in sort.split(',') if c.strip()]
    valid_sorts = [c for c in sort_cols if c in allowed_sorts] or [default_sort]
    order_clause = ','.join(f"{c}.{order}" for c in valid_sorts)
    params = {'select': '*', 'limit': str(limit), 'offset': str(offset), 'order': order_clause}
    search = query_params.get('search')
    if search:
        ilikes = ','.join(f"{c}.ilike.*{quote(search)}*" for c in search_columns)
        params['or'] = f"({ilikes})"
    meta = {'limit': limit, 'offset': offset, 'sort': ','.join(valid_sorts), 'order': order, 'search': search or None}
    return params, meta

def parse_total_from_content_range(value: str | None) -> int | None:
    if not value:
        return None
    try:
        total_part = value.split('/')[-1]
        return int(total_part) if total_part.isdigit() else None
    except Exception:
        return None

def supabase_headers(incoming_auth: str | None):
    anon = os.getenv('SUPABASE_ANON_KEY')
    apikey = anon or os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    headers = {'apikey': apikey, 'Accept': 'application/json', 'Prefer': 'count=exact'}
    if incoming_auth:
        headers['Authorization'] = incoming_auth
    return headers

def cache_headers(seconds: int):
    s = max(0, int(seconds))
    return {'Cache-Control': f'public, max-age={s}, s-maxage={s}, stale-while-revalidate={min(60, s)}'}
