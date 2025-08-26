import os
import json
import time
import base64
from typing import List, Dict, Any, Optional

from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from azure.core.exceptions import HttpResponseError, ServiceRequestError, ServiceResponseError

# Use your existing logger helper. If you don't have it, fallback to std logging.
try:
    from shared.logging_utils import get_logger
    logger = get_logger("altus.ai.client")
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("altus.ai.client")

# =====================
# Config
# =====================
# For Azure AI Foundry *project endpoints*, 2024-04-01-preview is the correct REST version.
DEFAULT_API_VERSION = os.environ.get("AZURE_AI_FOUNDRY_API_VERSION", "2024-04-01-preview")
FORCE_REST = os.environ.get("AZURE_AI_FOUNDRY_FORCE_REST", "false").lower() == "true"
AAD_SCOPE = "https://ai.azure.com/.default"  # Required scope for Foundry project endpoints

def _log_token_claims(token: str) -> None:
    """Log aud/iss/exp for troubleshooting (never logs the token)."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return
        pad = "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + pad).decode("utf-8"))
        aud = payload.get("aud")
        iss = payload.get("iss")
        exp = payload.get("exp")
        exp_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(exp)) if exp else None
        logger.info("AAD token claims: aud=%s iss=%s exp=%s", aud, iss, exp_iso)
    except Exception as e:
        logger.warning("Failed to log token claims: %s", e)

def _get_sdk_bits():
    try:
        from azure.ai.inference import ChatCompletionsClient
        from azure.core.credentials import AzureKeyCredential
        return ChatCompletionsClient, AzureKeyCredential
    except Exception as e:
        logger.warning("SDK not available, using raw HTTP: %s", e)
        return None, None

def _get_aad_token(scope: str) -> Optional[str]:
    """
    Prefer ManagedIdentityCredential (Function App MSI) and fall back to a constrained
    DefaultAzureCredential (avoids picking up local env/CLI creds).
    """
    try:
        from azure.identity import ManagedIdentityCredential, DefaultAzureCredential
        try:
            mi = ManagedIdentityCredential()
            token = mi.get_token(scope).token
            _log_token_claims(token)
            return token
        except Exception as mi_err:
            logger.warning("ManagedIdentityCredential failed: %s", mi_err)
            dac = DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_shared_token_cache_credential=True,
                exclude_visual_studio_code_credential=True,
                exclude_powershell_credential=True,
                exclude_interactive_browser_credential=True,
                exclude_cli_credential=True  # avoid accidental local 'az' profile
            )
            token = dac.get_token(scope).token
            _log_token_claims(token)
            return token
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
    """Foundry REST expects content to be an array of {type:'text', text:'...'}."""
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
    def __init__(self, endpoint: Optional[str] = None, key: Optional[str] = None, model: Optional[str] = None):
        self.endpoint = (endpoint or os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT", "")).rstrip("/")
        self.key = key or os.environ.get("AZURE_AI_FOUNDRY_KEY")
        self.default_model = model or os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-4o-mini")
        self.auth_mode = (os.environ.get("AZURE_AI_FOUNDRY_AUTH", "aad")).lower()
        self.api_version = os.environ.get("AZURE_AI_FOUNDRY_API_VERSION", DEFAULT_API_VERSION)

        if not self.endpoint:
            raise RuntimeError("Missing Foundry endpoint. Set AZURE_AI_FOUNDRY_ENDPOINT.")

        self._sdk_client = None
        if not FORCE_REST:
            self._init_sdk()

        logger.info(
            "Foundry client initialized: auth=%s force_rest=%s api_version=%s endpoint=%s",
            self.auth_mode, FORCE_REST, self.api_version, self.endpoint
        )

    def _init_sdk(self):
        ChatCompletionsClient, AzureKeyCredential = _get_sdk_bits()
        if ChatCompletionsClient is None:
            return

        if self.auth_mode == "aad":
            # Wrap DAC to force the exact Foundry scope regardless of internal SDK asks.
            from azure.identity import DefaultAzureCredential
            class _ScopeAdapter:
                def __init__(self, inner):
                    self._inner = inner
                def get_token(self, *_, **__):  # ignore requested scopes; always use Foundry
                    return self._inner.get_token(AAD_SCOPE)

            credential = _ScopeAdapter(DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_shared_token_cache_credential=True,
                exclude_visual_studio_code_credential=True,
                exclude_powershell_credential=True,
                exclude_interactive_browser_credential=True,
            ))
            self._sdk_client = ChatCompletionsClient(endpoint=self.endpoint, credential=credential)
            logger.info("Initialized SDK client with AAD (scope forced to %s).", AAD_SCOPE)
        else:
            if not self.key:
                raise RuntimeError("AZURE_AI_FOUNDRY_KEY is required for key auth.")
            self._sdk_client = ChatCompletionsClient(endpoint=self.endpoint, credential=AzureKeyCredential(self.key))
            logger.info("Initialized SDK client with api-key auth.")

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_random_exponential(multiplier=0.5, max=6.0),
        retry=retry_if_exception_type((HttpResponseError, ServiceRequestError, ServiceResponseError))
    )
    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """Send a chat completion via SDK (preferred) or REST fallback."""
        use_model = model or self.default_model

        # SDK path (preferred; avoids version pinning)
        if self._sdk_client and not FORCE_REST:
            sdk_messages = [_to_sdk_message(m) for m in messages]
            resp = self._sdk_client.complete(
                model=use_model,
                messages=sdk_messages,
                temperature=temperature
            )
            choice = resp.choices[0]
            parts = getattr(choice.message, "content", None) or []
            text = "".join(getattr(p, "text", "") or "" for p in parts)
            return text.strip()

        # REST path (if forced)
        import requests
        url = f"{self.endpoint}/chat/completions?api-version={self.api_version}"
        headers = {"Content-Type": "application/json"}

        if self.auth_mode == "aad":
            token = _get_aad_token(AAD_SCOPE)
            if not token:
                raise RuntimeError("Failed to acquire AAD token for https://ai.azure.com/.default")
            headers["Authorization"] = f"Bearer {token}"
        else:
            if not self.key:
                raise RuntimeError("AZURE_AI_FOUNDRY_KEY is required for key auth.")
            headers["api-key"] = self.key

        body = {
            "model": use_model,
            "messages": [_to_rest_message(m) for m in messages],
            "temperature": temperature
        }
        if max_output_tokens is not None:
            body["max_tokens"] = int(max_output_tokens)

        r = requests.post(url, headers=headers, json=body, timeout=30)
        if r.status_code in (401, 403):
            try:
                err = r.json()
            except Exception:
                err = r.text
            raise HttpResponseError(message=f"{r.status_code} from Foundry: {err}", response=r)

        if r.status_code == 400:
            try:
                err = r.json()
            except Exception:
                err = r.text
            # Helpful hint for recurring issue
            if "API version not supported" in str(err) or "Api version not supported" in str(err):
                raise HttpResponseError(
                    message=("400 from Foundry: API version not supported. "
                             "Set AZURE_AI_FOUNDRY_API_VERSION=2024-04-01-preview "
                             "or set AZURE_AI_FOUNDRY_FORCE_REST=false to prefer SDK."),
                    response=r
                )
            raise HttpResponseError(message=f"400 from Foundry: {err}", response=r)

        if r.status_code >= 500:
            raise HttpResponseError(message=f"{r.status_code} Server Error from Foundry", response=r)

        r.raise_for_status()
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return json.dumps(data)
