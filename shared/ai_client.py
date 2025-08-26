import os
import json
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from azure.core.exceptions import HttpResponseError, ServiceRequestError, ServiceResponseError
from shared.logging_utils import get_logger

logger = get_logger("altus.ai.client")

DEFAULT_API_VERSION = os.environ.get("AZURE_AI_FOUNDRY_API_VERSION", "2024-10-01-preview")
FORCE_REST = os.environ.get("AZURE_AI_FOUNDRY_FORCE_REST", "false").lower() == "true"

def _get_sdk_bits():
    try:
        from azure.ai.inference import ChatCompletionsClient
        from azure.core.credentials import AzureKeyCredential
        return ChatCompletionsClient, AzureKeyCredential
    except Exception as e:
        logger.warning("SDK not available, using raw HTTP: %s", e)
        return None, None

def _get_aad_token(scope: str) -> Optional[str]:
    try:
        from azure.identity import DefaultAzureCredential
        cred = DefaultAzureCredential()
        token = cred.get_token(scope)
        return token.token
    except Exception as e:
        logger.error("DefaultAzureCredential failed: %s", e)
        return None

def _to_sdk_message(msg):
    from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage, TextContentItem
    role = msg.get("role")
    content = msg.get("content")
    if isinstance(content, str):
        content = [TextContentItem(text=content)]
    elif isinstance(content, list):
        # assume already a list of TextContentItem-like; convert text entries
        new_items = []
        for item in content:
            if isinstance(item, str):
                new_items.append(TextContentItem(text=item))
            elif isinstance(item, dict) and "text" in item:
                new_items.append(TextContentItem(text=item["text"]))
        content = new_items or [TextContentItem(text="")]
    if role == "system":
        return SystemMessage(content=content)
    elif role == "assistant":
        return AssistantMessage(content=content)
    else:
        return UserMessage(content=content)

def _to_rest_message(msg: Dict[str, Any]) -> Dict[str, Any]:
    # Foundry REST expects: {"role": "...", "content": [{"type":"text","text":"..."}]}
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
                # allow {"text": "..."} or {"type":"text","text":"..."}
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
        self.auth_mode = (os.environ.get("AZURE_AI_FOUNDRY_AUTH", "key")).lower()
        self.api_version = os.environ.get("AZURE_AI_FOUNDRY_API_VERSION", DEFAULT_API_VERSION)
        if not self.endpoint:
            raise RuntimeError("Missing Foundry endpoint. Set AZURE_AI_FOUNDRY_ENDPOINT.")
        self._sdk_client = None
        if not FORCE_REST:
            self._init_sdk()
        logger.info("Foundry client using auth_mode=%s, force_rest=%s, api_version=%s", self.auth_mode, FORCE_REST, self.api_version)

    def _init_sdk(self):
        ChatCompletionsClient, AzureKeyCredential = _get_sdk_bits()
        if ChatCompletionsClient is None:
            return
        if self.auth_mode == "aad":
            class _TokenCred:
                def get_token(self, *scopes, **kwargs):
                    token = _get_aad_token("https://ai.azure.com/.default")
                    if not token:
                        raise RuntimeError("Failed to acquire AAD token for https://ai.azure.com/.default")
                    import time
                    class _T:
                        def __init__(self, t): self.token=t; self.expires_on=int(time.time())+3000
                    return _T(token)
            self._sdk_client = ChatCompletionsClient(endpoint=self.endpoint, credential=_TokenCred())
        else:
            if not self.key:
                raise RuntimeError("AZURE_AI_FOUNDRY_KEY is required for key auth.")
            self._sdk_client = ChatCompletionsClient(endpoint=self.endpoint, credential=AzureKeyCredential(self.key))

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
        if len(json.dumps(messages)) > 120_000:
            raise ValueError("Prompt too large. Reduce message size.")

        use_model = model or self.default_model

        if self._sdk_client and not FORCE_REST:
            sdk_messages = [_to_sdk_message(m) for m in messages]
            resp = self._sdk_client.complete(
                model=use_model,
                messages=sdk_messages,
                temperature=temperature
            )
            choice = resp.choices[0]
            parts = getattr(choice.message, "content", None) or []
            text = ""
            for p in parts:
                t = getattr(p, "text", None)
                if t:
                    text += t
            return text.strip()

        # Raw HTTP with correct REST message shape
        import requests
        url = f"{self.endpoint}/chat/completions?api-version={self.api_version}"
        headers = {"Content-Type": "application/json"}
        if self.auth_mode == "aad":
            token = _get_aad_token("https://ai.azure.com/.default")
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
            raise HttpResponseError(message=f"400 from Foundry: {err}", response=r)
        if r.status_code >= 500:
            raise HttpResponseError(message=f"{r.status_code} Server Error from Foundry", response=r)
        r.raise_for_status()
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return json.dumps(data)
