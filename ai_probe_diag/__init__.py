import json
import os
import sys
import platform
import azure.functions as func

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

def main(req: func.HttpRequest) -> func.HttpResponse:
    info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "app_root_in_path": APP_ROOT in sys.path,
        "env_present": {
            "AZURE_AI_FOUNDRY_ENDPOINT": bool(os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")),
            "AZURE_AI_FOUNDRY_KEY": bool(os.getenv("AZURE_AI_FOUNDRY_KEY")),
            "AZURE_AI_FOUNDRY_MODEL": os.getenv("AZURE_AI_FOUNDRY_MODEL"),
        },
        "imports": {}
    }

    # Try imports and record any errors as strings
    def tryimp(name, expr):
        try:
            mod = __import__(expr, fromlist=["*"])
            info["imports"][name] = "ok"
        except Exception as e:
            info["imports"][name] = f"ERR: {e.__class__.__name__}: {e}"

    tryimp("shared.ai_client", "shared.ai_client")
    tryimp("tenacity", "tenacity")
    tryimp("azure.ai.inference", "azure.ai.inference")
    tryimp("azure.core", "azure.core")

    return func.HttpResponse(json.dumps(info, default=str), mimetype="application/json", status_code=200)
