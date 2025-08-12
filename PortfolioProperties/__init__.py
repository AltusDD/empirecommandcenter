import azure.functions as func
from .common import properties
def main(req: func.HttpRequest) -> func.HttpResponse:
    return properties(req)
