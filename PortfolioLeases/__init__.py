import azure.functions as func
from .common import handle

def main(req: func.HttpRequest) -> func.HttpResponse:
    return handle("leases_enriched_v", req)
