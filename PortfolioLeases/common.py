import azure.functions as func
import json, os
from shared.supa import rest_get, ECC_CACHE_SECONDS, ECC_DEBUG

def normalize(req: func.HttpRequest):
    params = {}
    for k in req.params:
        params[k] = req.params.get(k)
    if "limit" not in params: params["limit"] = "25"
    if "offset" not in params: params["offset"] = "0"
    return params

def respond_ok(data):
    body = json.dumps(data)
    return func.HttpResponse(body, status_code=200, mimetype="application/json",
                             headers={"Cache-Control": f"public, max-age={ECC_CACHE_SECONDS}",
                                      "X-ECC-Debug": "1" if ECC_DEBUG else "0"})

def respond_err(res):
    payload = {"error": "upstream_error", "status": res.get("status")}
    if ECC_DEBUG:
        # Include helpful context only when DEBUG on
        for k in ("url","params","content_type","content_range","text_snippet","error"):
            v = res.get(k)
            if v is not None: payload[k] = v
    body = json.dumps(payload)
    return func.HttpResponse(body, status_code=res.get("status", 500), mimetype="application/json",
                             headers={"Cache-Control":"no-store","X-ECC-Debug": "1" if ECC_DEBUG else "0"})

def handle(view_name: str, req: func.HttpRequest) -> func.HttpResponse:
    res = rest_get(view_name, normalize(req))
    if res.get("ok") and isinstance(res.get("data"), (list, dict)):
        return respond_ok(res["data"])
    return respond_err(res)
