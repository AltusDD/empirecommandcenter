import os
import json
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from azure.core.exceptions import HttpResponseError, ServiceRequestError, ServiceResponseError
from shared.logging_utils import get_logger

logger = get_logger("altus.ai.client")

# ========= Config =========
# Fallback for old API versions has been removed. We will use a single, explicit version.
DEFAULT_API_VERSION = os.environ.get("AZURE_AI_FOUNDRY_API_VERSION", "2024-04-01-preview")
FORCE_REST = os.environ.get("AZURE_AI_FOUNDRY_FORCE_REST", "false").lower() == "true"
# Cache the working api-version for the process lifetime
_WORKING_API_VERSION: Optional[str] = None

# We'll use the SDK for building messages, as it's more robust
def _to_sdk_message(msg):
    # Lazy imports to avoid cold-start crashes if deps are missing
    from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage, TextContentItem
    role = msg.get("role")
    content = msg.get("content")
    if isinstance(content, str):
        content = [TextContentItem(text=content)]
    elif isinstance(content, list):
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
        try:
            from azure.ai.inference import ChatCompletionsClient
            from azure.core.credentials import AzureKeyCredential
            from azure.identity import DefaultAzureCredential
        except ImportError:
            logger.warning("Azure AI Inference or Azure Identity SDK not available, falling back to raw HTTP.")
            return

        # Use AAD with a managed identity if configured
        if self.auth_mode == "aad":
            try:
                # DefaultAzureCredential will automatically find the MI token
                credential = DefaultAzureCredential()
                self._sdk_client = ChatCompletionsClient(endpoint=self.endpoint, credential=credential)
                logger.info("Initialized Foundry SDK client with AAD managed identity.")
            except Exception as e:
                logger.error("Failed to initialize Foundry SDK client with AAD: %s", e)
        # Fallback to key-based auth
        else:
            if not self.key:
                raise RuntimeError("AZURE_AI_FOUNDRY_KEY is required for key auth.")
            self._sdk_client = ChatCompletionsClient(endpoint=self.endpoint, credential=AzureKeyCredential(self.key))
            logger.info("Initialized Foundry SDK client with API key.")

    def _rest_call(self, body: Dict[str, Any], api_version: str) -> Dict[str, Any]:
        import requests
        from azure.identity import DefaultAzureCredential
        
        url = f"{self.endpoint}/chat/completions?api-version={api_version}"
        headers = {"Content-Type": "application/json"}
        
        if self.auth_mode == "aad":
            try:
                cred = DefaultAzureCredential()
                token = cred.get_token("https://ai.azure.com/.default")
                headers["Authorization"] = f"Bearer {token.token}"
            except Exception as e:
                raise RuntimeError(f"Failed to acquire AAD token: {e}")
        else:
            if not self.key:
                raise RuntimeError("AZURE_AI_FOUNDRY_KEY is required for key auth.")
            headers["api-key"] = self.key

        r = requests.post(url, headers=headers, json=body, timeout=30)
        
        if r.status_code in (401, 403, 400):
            try: err = r.json()
            except Exception: err = r.text
            raise HttpResponseError(message=f"{r.status_code} from Foundry: {err}", response=r)
        if r.status_code >= 500:
            raise HttpResponseError(message=f"{r.status_code} Server Error from Foundry", response=r)
            
        r.raise_for_status()
        return r.json()

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
        # Guard big prompts
        if len(json.dumps(messages)) > 120_000:
            raise ValueError("Prompt too large. Reduce message size.")

        use_model = model or self.default_model

        # SDK path (preferred)
        if self._sdk_client and not FORCE_REST:
            sdk_messages = [_to_sdk_message(m) for m in messages]
            resp = self._sdk_client.complete(
                model=use_model,
                messages=sdk_messages,
                temperature=temperature
            )
            # The SDK response format is different, we need to parse it correctly
            choice = resp.choices[0]
            parts = getattr(choice.message, "content", None) or []
            text = "".join(getattr(p, "text", "") or "" for p in parts)
            return text.strip()

        # REST path (fallback)
        body = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature
        }
        if max_output_tokens is not None:
            body["max_tokens"] = int(max_output_tokens)

        try:
            data = self._rest_call(body, self.api_version)
            logger.info("Foundry REST succeeded with api-version=%s", self.api_version)
            return data["choices"][0]["message"]["content"]
        except HttpResponseError as e:
            logger.warning("Foundry REST call failed with: %s", str(e))
            raise e
