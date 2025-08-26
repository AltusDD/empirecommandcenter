
import json, os, sys
import azure.functions as func
from uuid import uuid4

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from shared.ai_client import FoundryClient
from shared.logging_utils import get_logger
logger = get_logger("altus.ai.summarize")

SYSTEM_PROMPT = """You are a concise assistant. Summarize the provided text.
- Be accurate and neutral.
- If 'style' is bullet, return 3–7 bullets.
- If 'style' is brief, return 1 short paragraph.
- If 'style' is detailed, return 2–3 short paragraphs.
"""

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

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        return _bad_request("'text' is required")

    style = (payload.get("style") or "brief").lower()
    if style not in ("brief","bullet","detailed"):
        style = "brief"

    model = payload.get("model") or os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-4o-mini")
    temperature = float(payload.get("temperature", 0.2))
    max_out = payload.get("max_output_tokens", 512)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + f"\nReturn style: {style}."},
        {"role": "user", "content": text}
    ]

    try:
        client = FoundryClient()
        summary = client.chat(messages=messages, temperature=temperature, max_output_tokens=max_out, model=model)
        return func.HttpResponse(
            json.dumps({"ok": True, "model": "foundry", "style": style, "summary": summary, "corr_id": corr_id}),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logger.exception("ai_summarize failed [%s]", corr_id)
        return func.HttpResponse(
            json.dumps({"ok": False, "error": str(e), "corr_id": corr_id}),
            mimetype="application/json",
            status_code=500,
        )
