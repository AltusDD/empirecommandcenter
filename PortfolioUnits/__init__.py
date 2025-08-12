import azure.functions as func
from .common import handle

def main(req: func.HttpRequest) -> func.HttpResponse:
    return handle('units_v', req)
