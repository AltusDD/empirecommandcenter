import azure.functions as func
import json, datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    now = datetime.datetime.utcnow().isoformat() + "Z"
    body = {
        "generated_at": now,
        "totals": {"properties": 0, "units": 0, "leases": 0, "tenants": 0},
        "kpis": {"occupancy_pct": None, "churn_30d": None},
        "source": "placeholder"
    }
    return func.HttpResponse(json.dumps(body), status_code=200, mimetype="application/json")
