import os
from typing import List, Dict, Any, Optional

from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from azure.core.exceptions import HttpResponseError, ServiceRequestError, ServiceResponseError

# Logger (use your shared helper if present)
try:
    from shared.logging_utils import get_logger
    logger = get_logger("altus.ai.client")
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("altus.ai.client")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_API_VERSION = os.environ.get("AZURE_AI_FOUNDRY_API_VERSION", "2024-04-01-preview")
FORCE_REST = os.environ.get("AZURE_AI_FOUNDRY_FORCE_REST", "false").lower() == "true"
AAD_SCOPE = "https://ai.azure.com/.default"  # for AAD flows against Foundry project endpoints

def _get_sdk_bits():
    """SDK path is optional; REST fallback is always available."""
    try:
        from azure.ai.inference import ChatCompletionsClient
        from azure.core.credentials import AzureKeyCredential
        return ChatCompletionsClient, AzureKeyCredential
    except Exception as e:
        logger.info("azure.ai.inference SDK not available; using REST. (%s)", e)
        return None, None

def _get_aad_token(scope: str) -> Optional[str]:
    """Acquire an AAD token (used only if AZURE_AI_FOUNDRY_AUTH=aad)."""
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
                exclude_powershell_credential=True,
                exclude_interactive_browser_credential=True,
                exclude_cli_credential=True,
            )
            return dac.get_token(scope).token
    except Exception as e:
        logger.error("AAD credential acquisition failed: %s", e)
        return None

def _to_sdk_message(msg: Dict[str, Any]):
    from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage, TextContentItem
    role = msg.get("role", "user")
    content = msg.get("content", "")
    items = []
    if isinstance(content, str):
        items = [TextContentItem(text=content)]
    elif isinstance(content, list):
        for it in content:
            if isinstance(it, str):
                items.append(TextContentItem(text=it))
            elif isinstance(it, dict) and "text" in it:
                items.append(TextContentItem(text=it["text"]))
    else:
        items = [TextContentItem(text=str(content))]
    if role == "system":
        return SystemMessage(content=items)
    elif role == "assistant":
        return AssistantMessage(content=items)
    else:
        return UserMessage(content=items)

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
    """Unified client for Azure AI Foundry project endpoints or Azure OpenAI endpoints."""
    def __init__(self, endpoint: Optional[str] = None, key: Optional[str] = None, model: Optional[str] = None):
        self.endpoint = (endpoint or os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT", "")).rstrip("/")
        self.key = key or os.environ.get("AZURE_AI_FOUNDRY_KEY")
        self.default_model = model or os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-4o-mini")
        self.auth_mode = (os.environ.get("AZURE_AI_FOUNDRY_AUTH", "aad")).lower()   # "aad" or "key"
        self.api_version = os.environ.get("AZURE_AI_FOUNDRY_API_VERSION", DEFAULT_API_VERSION)
        if not self.endpoint:
            raise RuntimeError("Missing Foundry/OpenAI endpoint. Set AZURE_AI_FOUNDRY_ENDPOINT.")

        self._sdk_client = None
        if not FORCE_REST:
            self._init_sdk()

        logger.info("FoundryClient init: endpoint=%s auth=%s api_version=%s force_rest=%s",
                    self.endpoint, self.auth_mode, self.api_version, FORCE_REST)

    def _init_sdk(self):
        ChatCompletionsClient, AzureKeyCredential = _get_sdk_bits()
        if ChatCompletionsClient is None:
            return
        if self.auth_mode == "aad":
            from azure.identity import DefaultAzureCredential
            cred = DefaultAzureCredential()
            try:
                cred.get_token(AAD_SCOPE)
                self._sdk_client = ChatCompletionsClient(endpoint=self.endpoint, credential=cred)
                logger.info("SDK client ready (AAD).")
            except Exception as e:
                logger.error("Failed to init SDK (AAD): %s", e)
                self._sdk_client = None
        else:
            if not self.key:
                raise RuntimeError("AZURE_AI_FOUNDRY_KEY required for key auth.")
            self._sdk_client = ChatCompletionsClient(endpoint=self.endpoint, credential=AzureKeyCredential(self.key))
            logger.info("SDK client ready (api-key).")

    def _rest_call(self, body: Dict[str, Any], api_version: str, deployment: str) -> Dict[str, Any]:
        import requests
        # IMPORTANT: Azure OpenAI endpoints require /openai/deployments/{deployment}/...
        url = f"{self.endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        headers = {"Content-Type": "application/json"}
        if self.auth_mode == "aad":
            token = _get_aad_token(AAD_SCOPE)
            if not token:
                raise RuntimeError("Failed to acquire AAD token for https://ai.azure.com/.default")
            headers["Authorization"] = f"Bearer {token}"
        else:
            if not self.key:
                raise RuntimeError("AZURE_AI_FOUNDRY_KEY required for key auth.")
            headers["api-key"] = self.key

        r = requests.post(url, headers=headers, json=body, timeout=30)
        if r.status_code in (400, 401, 403, 404):
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise HttpResponseError(message=f"{r.status_code} from Foundry/OpenAI: {detail}", response=r)
        if r.status_code >= 500:
            raise HttpResponseError(message=f"{r.status_code} server error from Foundry/OpenAI", response=r)
        r.raise_for_status()
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
        """
        Send a chat completion. `model` is the deployment name when using Azure OpenAI endpoints.
        """
        use_model = (model or self.default_model)

        # SDK path (if available)
        if self._sdk_client and not FORCE_REST:
            sdk_messages = [_to_sdk_message(m) for m in messages]
            resp = self._sdk_client.complete(
                model=use_model,
                messages=sdk_messages,
                temperature=temperature,
            )
            choice = resp.choices[0]
            parts = getattr(choice.message, "content", None) or []
            text = "".join(getattr(p, "text", "") or "" for p in parts)
            return text.strip()

        # REST path
        body = {
            "model": use_model,
            "messages": [_to_rest_message(m) for m in messages],
            "temperature": temperature,
        }
        if max_output_tokens is not None:
            body["max_tokens"] = int(max_output_tokens)

        data = self._rest_call(body, self.api_version, deployment=use_model)
        return data["choices"][0]["message"]["content"]
