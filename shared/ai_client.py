# shared/ai_client.py
import os
import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from azure.core.exceptions import HttpResponseError, ServiceRequestError, ServiceResponseError

# ---------- logging ----------
logger = logging.getLogger("altus.ai.client")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# ---------- config from env (kept your existing names) ----------
AUTH_MODE = os.environ.get("AZURE_AI_FOUNDRY_AUTH", "key").lower()               # "key" or "aad"
ENDPOINT = (os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT", "")).rstrip("/")
API_VERSION = os.environ.get("AZURE_AI_FOUNDRY_API_VERSION", "2025-01-01-preview")
MODEL_OR_DEPLOYMENT = os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-4o-mini")    # for AOAI: deployment name
API_KEY = os.environ.get("AZURE_AI_FOUNDRY_KEY")
FORCE_REST = os.environ.get("AZURE_AI_FOUNDRY_FORCE_REST", "true").lower() == "true"

AAD_SCOPE = "https://ai.azure.com/.default"  # Only used for Models endpoints if AUTH_MODE == aad

def _endpoint_kind(endpoint: str) -> str:
    """
    Returns 'aoai' for Azure OpenAI (cognitiveservices) endpoints,
            'models' for Azure AI Foundry 'models.ai.azure.com' endpoints.
    """
    host = urlparse(endpoint).hostname or ""
    if "cognitiveservices.azure.com" in host:
        return "aoai"
    if "models.ai.azure.com" in host:
        return "models"
    # Default to models if unsure
    return "models"

def _aad_token(scope: str) -> Optional[str]:
    """Get an AAD token (Managed Identity / DefaultAzureCredential)."""
    try:
        from azure.identity import ManagedIdentityCredential, DefaultAzureCredential
        try:
            mi = ManagedIdentityCredential()
            return mi.get_token(scope).token
        except Exception as mi_err:
            logger.warning("ManagedIdentityCredential failed: %s", mi_err)
            dac = DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_shared_token_cache_credential=True,
                exclude_visual_studio_code_credential=True,
                exclude_powershell_credential=True,  # typo fixed
                exclude_interactive_browser_credential=True,
                exclude_cli_credential=True,
            )
            return dac.get_token(scope).token
    except Exception as e:
        logger.error("Failed to get AAD token: %s", e)
        return None

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

class FoundryClient:
    """
    REST-only client that supports BOTH:
      • Azure OpenAI endpoints (cognitiveservices): /openai/deployments/{deployment}/chat/completions
      • Models endpoints (models.ai.azure.com): /chat/completions with 'model' in body
    Auth modes:
      • key  -> uses AZURE_AI_FOUNDRY_KEY header (api-key or Authorization)
      • aad  -> uses MSI/DefaultAzureCredential (scope https://ai.azure.com/.default for models)
    """

    def __init__(self,
                 endpoint: Optional[str] = None,
                 key: Optional[str] = None,
                 model: Optional[str] = None,
                 api_version: Optional[str] = None,
                 auth_mode: Optional[str] = None):
        self.endpoint = (endpoint or ENDPOINT).rstrip("/")
        self.key = key or API_KEY
        self.model = model or MODEL_OR_DEPLOYMENT
        self.api_version = api_version or API_VERSION
        self.auth_mode = (auth_mode or AUTH_MODE).lower()

        if not self.endpoint:
            raise RuntimeError("Missing endpoint. Set AZURE_AI_FOUNDRY_ENDPOINT.")
        if self.auth_mode == "key" and not self.key:
            raise RuntimeError("AZURE_AI_FOUNDRY_KEY is required for key auth.")

        self.kind = _endpoint_kind(self.endpoint)  # 'aoai' or 'models'
        logger.info("AI client init: kind=%s auth=%s api_version=%s endpoint=%s model=%s",
                    self.kind, self.auth_mode, self.api_version, self.endpoint, self.model)

    def _build_url(self) -> str:
        if self.kind == "aoai":
            # Azure OpenAI path requires deployments
            return f"{self.endpoint}/openai/deployments/{self.model}/chat/completions?api-version={self.api_version}"
        # Models path
        return f"{self.endpoint}/chat/completions?api-version={self.api_version}"

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_mode == "key":
            # Azure OpenAI expects 'api-key'; Models accepts 'api-key' or 'Authorization: Bearer'
            headers["api-key"] = self.key
            return headers
        # AAD
        scope = AAD_SCOPE if self.kind == "models" else "https://cognitiveservices.azure.com/.default"
        token = _aad_token(scope)
        if not token:
            raise RuntimeError(f"Failed to acquire AAD token for scope: {scope}")
        headers["Authorization"] = f"Bearer {token}"
        return headers

    def _build_body(self, messages: List[Dict[str, Any]], temperature: float, max_tokens: Optional[int]) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "messages": [_to_rest_message(m) for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            body["max_tokens"] = int(max_tokens)
        # For Models endpoint, pass the model name in the body
        if self.kind == "models":
            body["model"] = self.model
        # For Azure OpenAI, DO NOT include "model" in body (deployment already in the path)
        return body

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_random_exponential(multiplier=0.5, max=6.0),
        retry=retry_if_exception_type((HttpResponseError, ServiceRequestError, ServiceResponseError)),
    )
    def chat(self,
             messages: List[Dict[str, Any]],
             temperature: float = 0.2,
             max_output_tokens: Optional[int] = None) -> str:
        url = self._build_url()
        headers = self._build_headers()
        body = self._build_body(messages, temperature, max_output_tokens)

        resp = requests.post(url, headers=headers, json=body, timeout=30)
        if resp.status_code >= 400:
            # try to unwrap JSON error
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            if resp.status_code >= 500:
                raise HttpResponseError(message=f"{resp.status_code} Server Error: {detail}", response=resp)
            raise HttpResponseError(message=f"{resp.status_code} from service: {detail}", response=resp)

        data = resp.json()
        # unify text extraction
        try:
            return data["choices"][0]["message"]["content"] or ""
        except Exception:
            # some previews may return choices[0].delta or similar; fall back to dumping data for visibility
            logger.warning("Unexpected response shape: %s", json.dumps(data)[:500])
            return ""
