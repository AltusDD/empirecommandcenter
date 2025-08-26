import json
import logging
import uuid
import azure.functions as func

# lazy import client & logger to keep cold start small
def _lazy():
    try:
        from shared.ai_client import FoundryClient  # type: ignore
    except Exception as e:
        logging.exception("import_error: %s", e)
        raise
    # optional custom logger (safe fallback to std logging)
    try:
        from shared.logging_utils import get_logger  # type: ignore
        logger = get_logger("ai_chat")
    except Exception:
        logger = logging.getLogger("ai_chat")
    return FoundryClient, logger

def _bad_request(msg: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"ok": False, "error": msg}),
        status_code=400,
        mimetype="application/json",
    )

def main(req: func.HttpRequest) -> func.HttpResponse:
    corr_id = str(uuid.uuid4())
    try:
        FoundryClient, logger = _lazy()
        logger.info("ai_chat start corr_id=%s", corr_id)

        try:
            payload = req.get_json()
        except Exception:
            return _bad_request("Invalid JSON body.")

        # validate basic shape
        msgs = payload.get("messages")
        if not isinstance(msgs, list) or not msgs:
            return _bad_request('"messages" must be a non-empty array.')

        temperature = payload.get("temperature", 0.2)
        try:
            temperature = float(temperature)
        except Exception:
            temperature = 0.2

        model = payload.get("model")  # optional; defaults from env

        # call model
        client = FoundryClient()
        reply = client.chat(
            messages=msgs,
            temperature=temperature,
            model=model,
        )

        body = {
            "ok": True,
            "content": reply,
            "corr_id": corr_id,
        }
        return func.HttpResponse(
            json.dumps(body, ensure_ascii=False),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logging.exception("ai_chat unhandled error corr_id=%s", corr_id)
        return func.HttpResponse(
            json.dumps({"ok": False, "error": str(e), "corr_id": corr_id}),
            status_code=500,
            mimetype="application/json",
        )
