import json
import os
import sys
import azure.functions as func

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

def _lazy_imports():
    try:
        from shared.ai_client import FoundryClient  # type: ignore
        from shared.logging_utils import get_logger  # type: ignore
        return FoundryClient, get_logger, None
    except Exception as e:
        return None, None, e

def _validate(payload):
    if not isinstance(payload, dict):
        raise ValueError("JSON body required.")
    msgs = payload.get("messages")
    if not isinstance(msgs, list) or not msgs:
        raise ValueError("'messages' must be a non-empty array.")
    import json as _json
    encoded = _json.dumps(msgs)
    if len(encoded) > 120_000:
        raise ValueError("Prompt too large. Reduce message size.")
    temp = payload.get("temperature", 0.2)
    max_tokens = payload.get("max_output_tokens")
    if max_tokens is not None:
        try:
            max_tokens = int(max_tokens)
        except Exception:
            raise ValueError("'max_output_tokens' must be an integer.")
    mdl = payload.get("model")
    if mdl is not None and not isinstance(mdl, str):
        raise ValueError("'model' must be a string if provided.")
    return msgs, float(temp), max_tokens, mdl

def main(req: func.HttpRequest) -> func.HttpResponse:
    FoundryClient, get_logger, import_err = _lazy_imports()
    if import_err is not None:
        body = {"ok": False, "error": f"import_error: {import_err.__class__.__name__}: {import_err}"}
        return func.HttpResponse(json.dumps(body), mimetype="application/json", status_code=500)

    logger = get_logger("altus.ai.chat")
    try:
        payload = req.get_json()
        messages, temperature, max_tokens, model_override = _validate(payload)

        corr = req.headers.get("x-correlation-id")
        if not corr:
            import uuid
            corr = str(uuid.uuid4())
        logger.info("corr_id=%s ai_chat request", corr)

        miss = [k for k in ("AZURE_AI_FOUNDRY_ENDPOINT","AZURE_AI_FOUNDRY_KEY") if not os.getenv(k)]
        if miss:
            return func.HttpResponse(
                json.dumps({"ok": False, "error": f"missing_app_settings: {', '.join(miss)}"}),
                mimetype="application/json", status_code=500
            )

        client = FoundryClient()
        text = client.chat(
            messages,
            temperature=temperature,
            max_output_tokens=max_tokens,
            model=model_override
        )
        return func.HttpResponse(
            json.dumps({"ok": True, "content": text, "corr_id": corr}),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.exception("ai_chat failed")
        return func.HttpResponse(json.dumps({"ok": False, "error": str(e)}), mimetype="application/json", status_code=400)
