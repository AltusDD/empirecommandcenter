import azure.functions as func
import json, datetime
from shared.supa import table_count

def main(req: func.HttpRequest) -> func.HttpResponse:
    now = datetime.datetime.utcnow().isoformat() + "Z"
    props = table_count("properties")
    units = table_count("units")
    leases = table_count("leases")
    body = {
        "generated_at": now,
        "totals": {
            "properties": props,
            "units": units,
            "leases": leases,
        },
        "kpis": {
            "occupancy_pct": None
        },
        "source": "supabase_rest" if all(v is not None for v in [props, units, leases]) else "placeholder"
    }
    return func.HttpResponse(json.dumps(body), status_code=200, mimetype="application/json")
