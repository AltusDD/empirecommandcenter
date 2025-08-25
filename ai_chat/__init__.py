import json
import azure.functions as func
from shared.ai_client import FoundryClient
from shared.logging_utils import get_logger

logger = get_logger("altus.ai.chat")

def _validate(payload):
    if not isinstance(payload, dict):
        raise ValueError("JSON body required.")
    msgs = payload.get("messages")
    if not isinstance(msgs, list) or not msgs:
        raise ValueError("'messages' must be a non-empty array.")
    encoded = json.dumps(msgs)
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
    try:
        payload = req.get_json()
        messages, temperature, max_tokens, model_override = _validate(payload)

        corr = req.headers.get("x-correlation-id")
        if not corr:
            import uuid
            corr = str(uuid.uuid4())
        logger.info("corr_id=%s ai_chat request", corr)

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
