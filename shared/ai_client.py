# shared/ai_client.py
import os
from typing import List, Dict, Any
from openai import AzureOpenAI

# Env vars (use the names below)
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")  # e.g. https://altus-ops-foundry.cognitiveservices.azure.com/
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")            # project/deployment API key
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")  # your deployment name
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

_client: AzureOpenAI | None = None

def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_KEY:
            raise RuntimeError("Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_KEY")
        _client = AzureOpenAI(
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_KEY,
        )
    return _client

def simple_chat(user_text: str, system_text: str = "You are a helpful assistant.", temperature: float = 0.2) -> str:
    """
    Calls Azure OpenAI Chat Completions using the configured deployment.
    """
    client = _get_client()

    # Azure OpenAI: pass deployment via 'model' param (deployment name)
    resp = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        temperature=temperature,
    )
    # Extract first choice text
    choice = resp.choices[0]
    # Newer SDKs expose message.content as a string
    return getattr(choice.message, "content", "") or ""
