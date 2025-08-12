import azure.functions as func
import json, os, datetime

EXPOSE = ["WEBSITE_SITE_NAME","WEBSITE_INSTANCE_ID","REGION_NAME","WEBSITE_HOSTNAME","AZURE_FUNCTIONS_ENVIRONMENT"]

def main(req: func.HttpRequest) -> func.HttpResponse:
    env = {k: os.environ.get(k) for k in EXPOSE}
    body = {"env": env, "time": datetime.datetime.utcnow().isoformat() + "Z"}
    return func.HttpResponse(json.dumps(body), status_code=200, mimetype="application/json")
