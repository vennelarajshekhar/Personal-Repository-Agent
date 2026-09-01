from __future__ import annotations

from typing import Any

import httpx

from repo_agent.config import Settings


class LLMError(RuntimeError):
    pass


class LLMClient:
    """Minimal OpenAI-compatible chat client (OpenAI, Groq, vLLM, Ollama, etc.)."""

    def __init__(self, settings: Settings, timeout: float = 90.0):
        self.settings = settings
        self.timeout = timeout

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.settings.llm_configured:
            raise LLMError(
                "No LLM_API_KEY found. Add it to the .env file in the project root "
                "(copy .env.example) or set LLM_API_KEY / OPENAI_API_KEY."
            )
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }
        url = f"{self.settings.llm_base_url}/chat/completions"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc
        if response.status_code >= 400:
            raise LLMError(_format_http_error(response.status_code, response.text))
        data = response.json()
        try:
            return data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"unexpected LLM response: {data}") from exc


def _format_http_error(status: int, body: str) -> str:
    snippet = (body or "").strip().replace("\n", " ")[:400]
    if status in {401, 403}:
        return (
            f"LLM error {status}: API key was rejected. "
            "Check LLM_API_KEY in .env (OpenAI project keys start with sk-proj- or sk-). "
            f"Details: {snippet}"
        )
    if status == 404:
        return (
            f"LLM error 404: model or URL not found. "
            f"Check LLM_MODEL and LLM_BASE_URL in .env. Details: {snippet}"
        )
    if status == 429:
        return f"LLM error 429: rate limited or quota exceeded. Details: {snippet}"
    return f"LLM error {status}: {snippet}"
