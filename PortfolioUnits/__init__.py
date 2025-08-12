import azure.functions as func
from .common import units
def main(req: func.HttpRequest) -> func.HttpResponse:
    return units(req)
