import azure.functions as func
from .common import leases
def main(req: func.HttpRequest) -> func.HttpResponse:
    return leases(req)
