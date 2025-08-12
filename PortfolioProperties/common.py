import azure.functions as func
from urllib.parse import parse_qs
from shared.supa import rest_get

def normalize_params(req: func.HttpRequest):
    # pass through limit, offset, order, and any filters like column=eq.value
    params = {}
    for k in req.params:
        params[k] = req.params.get(k)
    # sensible defaults
    if "limit" not in params: params["limit"] = "25"
    if "offset" not in params: params["offset"] = "0"
    return params

def handle(table: str, req: func.HttpRequest) -> func.HttpResponse:
    params = normalize_params(req)
    data, code, extra = rest_get(table, params)
    if code >= 400:
        return func.HttpResponse(
            mimetype="application/json",
            status_code=code if code else 502,
            body=str(data).encode("utf-8") if isinstance(data, (dict,list)) else (data or "").encode("utf-8"),
        )
    return func.HttpResponse(
        mimetype="application/json",
        status_code=200,
        body=func._to_bytes(data) if hasattr(func, "_to_bytes") else (str(data).encode("utf-8"))
    )

def properties(req: func.HttpRequest) -> func.HttpResponse:
    return handle("properties", req)

def units(req: func.HttpRequest) -> func.HttpResponse:
    return handle("units", req)

def leases(req: func.HttpRequest) -> func.HttpResponse:
    return handle("leases", req)
