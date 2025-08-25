import json
import os
import sys
import azure.functions as func

# Ensure app root is on sys.path so 'shared' is importable in all layouts
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

# Lazy import to avoid cold-start crash when deps or path are missing
def _lazy_imports():
    try:
        from shared.ai_client import FoundryClient  # type: ignore
        from shared.logging_utils import get_logger  # type: ignore
        return FoundryClient, get_logger, None
    except Exception as e:
        return None, None, e

def main(req: func.HttpRequest) -> func.HttpResponse:
    FoundryClient, get_logger, import_err = _lazy_imports()
    if import_err is not None:
        # Import failed (likely shared not on path or missing deps). Return clear message.
        body = {"ok": False, "error": f"import_error: {import_err.__class__.__name__}: {import_err}"}
        return func.HttpResponse(json.dumps(body), mimetype="application/json", status_code=500)

    logger = get_logger("altus.ai.probe")
    try:
        q = req.params.get("q") or "Reply with 'pong' and the result of 2+2."
        corr = req.headers.get("x-correlation-id")
        if not corr:
            import uuid
            corr = str(uuid.uuid4())
        logger.info("corr_id=%s ai_probe", corr)

        # Quick env sanity for clearer 500s
        miss = [k for k in ("AZURE_AI_FOUNDRY_ENDPOINT","AZURE_AI_FOUNDRY_KEY") if not os.getenv(k)]
        if miss:
            return func.HttpResponse(
                json.dumps({"ok": False, "error": f"missing_app_settings: {', '.join(miss)}"}),
                mimetype="application/json", status_code=500
            )

        client = FoundryClient()
        txt = client.chat(
            [
                {"role": "system", "content": "You are a concise assistant. Respond with one short sentence."},
                {"role": "user",   "content": q}
            ],
            temperature=0.1,
            max_output_tokens=64
        )
        out = {"ok": True, "model": "foundry", "reply": txt, "corr_id": corr}
        return func.HttpResponse(json.dumps(out), mimetype="application/json", status_code=200)
    except Exception as e:
        logger.exception("AI probe failed")
        return func.HttpResponse(json.dumps({"ok": False, "error": str(e)}), mimetype="application/json", status_code=500)
