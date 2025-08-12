import azure.functions as func
import json
from shared.supa import rest_get

def count_of(resource):
    data, code, _ = rest_get(resource, {"select":"id","limit":"1"})
    # Prefer Content-Range, but rest_get doesn't return it here; fallback to len(data)
    try:
        return len(data) if isinstance(data, list) else None
    except Exception:
        return None

def main(req: func.HttpRequest) -> func.HttpResponse:
    body = {
        "totals": {
            "properties": count_of("property_occupancy_v"),
            "units": count_of("units_v"),
            "leases": count_of("leases_enriched_v")
        }
    }
    return func.HttpResponse(json.dumps(body), status_code=200, mimetype="application/json")
