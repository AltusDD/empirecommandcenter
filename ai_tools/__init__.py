
import json, os, sys
import azure.functions as func
from uuid import uuid4

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from shared.ai_client import FoundryClient
from shared.logging_utils import get_logger
logger = get_logger("altus.ai.tools")

def _bad_request(msg: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"ok": False, "error": msg}),
        mimetype="application/json",
        status_code=400,
    )

def main(req: func.HttpRequest) -> func.HttpResponse:
    corr_id = str(uuid4())
    try:
        payload = req.get_json()
    except Exception:
        return _bad_request("Invalid JSON body")

    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return _bad_request("'messages' must be a non-empty array")

    model = payload.get("model") or os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-4o-mini")
    temperature = float(payload.get("temperature", 0.2))
    max_out = payload.get("max_output_tokens")
    tools = payload.get("tools")
    tool_choice = payload.get("tool_choice")

    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if isinstance(max_out, int):
        body["max_output_tokens"] = max_out
    if tools:
        body["tools"] = tools
    if tool_choice:
        body["tool_choice"] = tool_choice

    try:
        client = FoundryClient()
        resp = client.raw_chat(body)
        choice = (resp.get("choices") or [{}])[0]
        message = choice.get("message", {})

        result = {
            "ok": True,
            "model": "foundry",
            "corr_id": corr_id,
            "content": message.get("content"),
        }
        if "tool_calls" in message:
            result["tool_calls"] = message["tool_calls"]
            result["type"] = "tool_calls"
        else:
            result["type"] = "message"

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logger.exception("ai_tools failed [%s]", corr_id)
        return func.HttpResponse(
            json.dumps({"ok": False, "error": str(e), "corr_id": corr_id}),
            mimetype="application/json",
            status_code=500,
        )
