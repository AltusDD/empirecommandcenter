import json
import azure.functions as func
from ..shared.ai_client import FoundryClient
from ..shared.logging_utils import get_logger

logger = get_logger("altus.ai.chat")

def _validate(payload):
    if not isinstance(payload, dict):
        raise ValueError("JSON body required.")
    msgs = payload.get("messages")
    if not isinstance(msgs, list) or not msgs:
        raise ValueError("'messages' must be a non-empty array.")
    # Trim overly large content early (basic guard)
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
    return msgs, float(temp), max_tokens

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        payload = req.get_json()
        messages, temperature, max_tokens = _validate(payload)
        client = FoundryClient()
        text = client.chat(messages, temperature=temperature, max_output_tokens=max_tokens)
        return func.HttpResponse(
            json.dumps({"ok": True, "content": text}),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.exception("ai_chat failed")
        return func.HttpResponse(json.dumps({"ok": False, "error": str(e)}), mimetype="application/json", status_code=400)
