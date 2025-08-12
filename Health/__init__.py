import azure.functions as func
import json, datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    now = datetime.datetime.utcnow().isoformat() + "Z"
    body = {"status": "ok", "app": "Empire Command Center", "time": now}
    return func.HttpResponse(json.dumps(body), status_code=200, mimetype="application/json")
