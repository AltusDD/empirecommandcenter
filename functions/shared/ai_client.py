import os
import json
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
from azure.core.exceptions import HttpResponseError, ServiceRequestError, ServiceResponseError

from .logging_utils import get_logger

logger = get_logger("altus.ai.client")

# Lazy import to keep cold start small; fallback if SDK missing for any reason
def _get_sdk_client():
    try:
        from azure.ai.inference import ChatCompletionsClient
        from azure.core.credentials import AzureKeyCredential
        return ChatCompletionsClient, AzureKeyCredential
    except Exception as e:
        logger.warning("Falling back to raw HTTP for Foundry calls: %s", e)
        return None, None

class FoundryClient:
    def __init__(self, endpoint: Optional[str] = None, key: Optional[str] = None, model: Optional[str] = None):
        self.endpoint = endpoint or os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT", "").rstrip("/")
        self.key = key or os.environ.get("AZURE_AI_FOUNDRY_KEY")
        self.model = model or os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-4o-mini")
        if not self.endpoint or not self.key:
            raise RuntimeError("Missing Foundry endpoint or key. Set AZURE_AI_FOUNDRY_ENDPOINT and AZURE_AI_FOUNDRY_KEY.")
        self._sdk_client = None
        self._init_sdk()

    def _init_sdk(self):
        ChatCompletionsClient, AzureKeyCredential = _get_sdk_client()
        if ChatCompletionsClient:
            self._sdk_client = ChatCompletionsClient(endpoint=self.endpoint, credential=AzureKeyCredential(self.key))

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential_jitter(initial=0.5, max=6.0),
        retry=retry_if_exception_type((HttpResponseError, ServiceRequestError, ServiceResponseError))
    )
    def chat(self, messages: List[Dict[str, Any]], temperature: float = 0.2, max_output_tokens: Optional[int] = None) -> str:
        # Basic size guard
        if len(json.dumps(messages)) > 120_000:  # ~120 KB of JSON
            raise ValueError("Prompt too large. Reduce message size.")

        # Prefer SDK
        if self._sdk_client:
            from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage, TextContentItem
            def to_sdk(msg):
                role = msg.get("role")
                content = msg.get("content")
                if isinstance(content, str):
                    content = [TextContentItem(text=content)]
                if role == "system":
                    return SystemMessage(content=content)
                elif role == "assistant":
                    return AssistantMessage(content=content)
                else:
                    return UserMessage(content=content)

            sdk_messages = [to_sdk(m) for m in messages]
            resp = self._sdk_client.complete(
                model=self.model,
                messages=sdk_messages,
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )
            # The SDK returns structured content items; text is in the first item typically
            choice = resp.choices[0]
            parts = choice.message.content or []
            text = ""
            for p in parts:
                t = getattr(p, "text", None)
                if t:
                    text += t
            return text.strip()

        # Fallback: raw HTTP
        import requests
        url = f"{self.endpoint}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "api-key": self.key
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        if max_output_tokens is not None:
            payload["max_output_tokens"] = max_output_tokens

        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if r.status_code == 429:
            # Let tenacity retry us
            raise HttpResponseError(message="429 Too Many Requests", response=r)
        if r.status_code >= 500:
            raise HttpResponseError(message=f"{r.status_code} Server Error", response=r)
        r.raise_for_status()
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return json.dumps(data)
