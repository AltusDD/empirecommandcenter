import azure.functions as func
import json
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
    res = rest_get(resource, params)
    status = res.get("status", 500)
    # Success -> return JSON data only
    if res.get("ok") and isinstance(res.get("data"), (list, dict)):
        body = json.dumps(res["data"])
        return func.HttpResponse(body, status_code=200, mimetype="application/json")
    # Otherwise return a debug payload (redacts key by not including headers)
    debug = {
        "error": "supabase_request_failed",
        "resource": resource,
        "status": status,
        "url": res.get("url"),
        "params": res.get("params"),
        "content_type": res.get("content_type"),
        "content_range": res.get("content_range"),
        "data_type": type(res.get("data")).__name__ if res.get("data") is not None else None,
        "text_snippet": res.get("text_snippet"),
        "exception": res.get("error")
    }
    return func.HttpResponse(json.dumps(debug), status_code=status or 500, mimetype="application/json")
