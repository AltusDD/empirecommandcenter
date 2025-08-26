import os
import json
from typing import Any, Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from azure.core.exceptions import HttpResponseError, ServiceRequestError, ServiceResponseError

# -------- logger (safe fallback) --------
try:
    from shared.logging_utils import get_logger
    logger = get_logger("altus.ai.client")
except Exception:  # pragma: no cover
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("altus.ai.client")

# -------- config --------
DEFAULT_API_VERSION = os.environ.get("AZURE_AI_FOUNDRY_API_VERSION", "2024-04-01-preview")
FORCE_REST = True  # using REST for Azure OpenAI endpoints

class FoundryClient:
    """
    Simple client for Azure OpenAI (cognitiveservices) chat completions using REST.
    Env required:
      - AZURE_AI_FOUNDRY_ENDPOINT: https://<res>.cognitiveservices.azure.com
      - AZURE_AI_FOUNDRY_MODEL:    <deployment-name> (e.g., gpt-4o-mini)
      - AZURE_AI_FOUNDRY_API_VERSION: 2024-04-01-preview
      - AZURE_AI_FOUNDRY_KEY:      <api key>
    """
    def __init__(self, endpoint: Optional[str] = None, key: Optional[str] = None, model: Optional[str] = None):
        self.endpoint = (endpoint or os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT", "")).rstrip("/")
        self.key = key or os.environ.get("AZURE_AI_FOUNDRY_KEY")
        self.default_model = model or os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-4o-mini")
        self.api_version = os.environ.get("AZURE_AI_FOUNDRY_API_VERSION", DEFAULT_API_VERSION)

        if not self.endpoint:
            raise RuntimeError("Missing AZURE_AI_FOUNDRY_ENDPOINT")
        if not self.key:
            raise RuntimeError("Missing AZURE_AI_FOUNDRY_KEY")

    def _rest_call(self, body: Dict[str, Any], model: str, api_version: str) -> Dict[str, Any]:
        import requests
        url = f"{self.endpoint}/openai/deployments/{model}/chat/completions?api-version={api_version}"
        headers = {
            "Content-Type": "application/json",
            "api-key": self.key,
        }
        r = requests.post(url, headers=headers, json=body, timeout=30)
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise HttpResponseError(message=f"{r.status_code} from service: {detail}", response=r)
        return r.json()

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_random_exponential(multiplier=0.5, max=6.0),
        retry=retry_if_exception_type((HttpResponseError, ServiceRequestError, ServiceResponseError)),
    )
    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ) -> str:
        use_model = model or self.default_model
        body: Dict[str, Any] = {
            "messages": [_to_rest_message(m) for m in messages],
            "temperature": temperature,
            "model": use_model
        }
        if max_output_tokens is not None:
            body["max_tokens"] = int(max_output_tokens)

        data = self._rest_call(body, use_model, self.api_version)
        # Azure OpenAI response shape
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            logger.warning("Unexpected response: %s", json.dumps(data)[:500])
            raise RuntimeError("Failed to parse model response.")

def _to_rest_message(msg: Dict[str, Any]) -> Dict[str, Any]:
    role = msg.get("role", "user")
    content = msg.get("content", "")
    items: List[Dict[str, str]] = []
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
