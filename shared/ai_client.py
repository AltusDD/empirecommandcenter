
import os
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from azure.core.exceptions import HttpResponseError, ServiceRequestError, ServiceResponseError

try:
    from shared.logging_utils import get_logger
    logger = get_logger("altus.ai.client")
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("altus.ai.client")

DEFAULT_API_VERSION = os.environ.get("AZURE_AI_FOUNDRY_API_VERSION", "2024-04-01-preview")
AAD_SCOPE = "https://ai.azure.com/.default"

class FoundryClient:
    """
    Minimal client for Azure OpenAI (Cognitive Services endpoint) chat completions.
    Uses API key auth by default (AZURE_AI_FOUNDRY_AUTH=key). AAD not enabled in this build.
    """
    def __init__(self, endpoint: Optional[str] = None, key: Optional[str] = None, model: Optional[str] = None):
        self.endpoint = (endpoint or os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT", "")).rstrip("/")
        self.key = key or os.environ.get("AZURE_AI_FOUNDRY_KEY")
        self.default_model = model or os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-4o-mini")
        self.api_version = os.environ.get("AZURE_AI_FOUNDRY_API_VERSION", DEFAULT_API_VERSION)
        self.auth_mode = (os.environ.get("AZURE_AI_FOUNDRY_AUTH", "key")).lower()
        if not self.endpoint:
            raise RuntimeError("Missing AZURE_AI_FOUNDRY_ENDPOINT")
        if self.auth_mode != "key":
            logger.warning("This build is configured for 'key' auth. Current auth=%s", self.auth_mode)

    def _rest_call(self, body: Dict[str, Any], api_version: str) -> Dict[str, Any]:
        import requests
        # Model is the deployment name for Azure OpenAI
        model = body.get("model") or self.default_model
        body["model"] = model

        url = f"{self.endpoint}/openai/deployments/{model}/chat/completions?api-version={api_version}"
        headers = {"Content-Type": "application/json"}
        if self.auth_mode == "key":
            if not self.key:
                raise RuntimeError("AZURE_AI_FOUNDRY_KEY is required for key auth.")
            headers["api-key"] = self.key
        else:
            raise RuntimeError("AAD auth not enabled in this build. Set AZURE_AI_FOUNDRY_AUTH=key.")

        r = requests.post(url, headers=headers, json=body, timeout=30)
        if r.status_code >= 400:
            try:
                err = r.json()
            except Exception:
                err = r.text
            raise HttpResponseError(message=f"{r.status_code} from Foundry: {err}", response=r)
        return r.json()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=0.5, max=4.0),
        retry=retry_if_exception_type((HttpResponseError, ServiceRequestError, ServiceResponseError))
    )
    def chat(self,
             messages: List[Dict[str, Any]],
             temperature: float = 0.2,
             max_output_tokens: Optional[int] = None,
             model: Optional[str] = None) -> str:
        body: Dict[str, Any] = {
            "messages": [_to_rest_message(m) for m in messages],
            "temperature": temperature,
        }
        if model:
            body["model"] = model
        if max_output_tokens is not None:
            body["max_tokens"] = int(max_output_tokens)
        data = self._rest_call(body, self.api_version)
        return _extract_text_from_resp(data)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=0.5, max=4.0),
        retry=retry_if_exception_type((HttpResponseError, ServiceRequestError, ServiceResponseError))
    )
    def raw_chat(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Pass-through helper for advanced features (tools, tool_choice, etc.)."""
        # Normalize messages and max tokens if the caller used alt names
        if "messages" in body:
            body["messages"] = [_to_rest_message(m) for m in body["messages"]]
        if "max_output_tokens" in body and "max_tokens" not in body:
            try:
                body["max_tokens"] = int(body.pop("max_output_tokens"))
            except Exception:
                body.pop("max_output_tokens", None)
        data = self._rest_call(body, self.api_version)
        return data

def _to_rest_message(msg: Dict[str, Any]) -> Dict[str, Any]:
    role = msg.get("role", "user")
    content = msg.get("content", "")
    items = []
    if isinstance(content, str):
        items = [{"type": "text", "text": content}]
    elif isinstance(content, list):
        for it in content:
            if isinstance(it, str):
                items.append({"type": "text", "text": it})
            elif isinstance(it, dict):
                t = it.get("text") or it.get("value") or ""
                items.append({"type": "text", "text": t})
    elif isinstance(content, dict):
        t = content.get("text") or content.get("value") or ""
        items.append({"type": "text", "text": t})
    if not items:
        items = [{"type": "text", "text": ""}]
    return {"role": role, "content": items}

def _extract_text_from_resp(data: Dict[str, Any]) -> str:
    try:
        choice = data["choices"][0]
        msg = choice.get("message", {})
        if isinstance(msg.get("content"), str):
            return msg.get("content", "").strip()
        # content may be a list of parts in some responses - handle gracefully
        parts = msg.get("content") or []
        if isinstance(parts, list):
            return "".join([p.get("text", "") for p in parts if isinstance(p, dict)]).strip()
        return str(msg.get("content", "")).strip()
    except Exception:
        return ""
