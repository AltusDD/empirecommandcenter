import azure.functions as func
from shared.supa import rest_get

def normalize_params(req: func.HttpRequest):
    params = {}
    for k in req.params:
        params[k] = req.params.get(k)
    if "limit" not in params: params["limit"] = "25"
    if "offset" not in params: params["offset"] = "0"
    return params

def handle(resource: str, req: func.HttpRequest) -> func.HttpResponse:
    params = normalize_params(req)
    data, code, _ = rest_get(resource, params)
    return func.HttpResponse(
        status_code=code or 502,
        mimetype="application/json",
        body=(func._to_bytes(data) if hasattr(func, "_to_bytes") else (str(data).encode("utf-8")))
    )
