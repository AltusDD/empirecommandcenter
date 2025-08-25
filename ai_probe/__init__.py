import json
import azure.functions as func
from shared.ai_client import FoundryClient
from shared.logging_utils import get_logger

logger = get_logger("altus.ai.probe")

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        q = req.params.get("q") or "Reply with 'pong' and the result of 2+2.'"
        corr = req.headers.get("x-correlation-id")
        if not corr:
            import uuid
            corr = str(uuid.uuid4())
        logger.info("corr_id=%s ai_probe", corr)

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
