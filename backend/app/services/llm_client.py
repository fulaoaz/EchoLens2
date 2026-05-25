"""OpenAI-compatible LLM client — chat / chat_json wrappers."""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.config import get_settings


def get_client() -> OpenAI:
    s = get_settings()
    return OpenAI(api_key=s.llm_api_key or "missing", base_url=s.llm_base_url)


def chat(messages: list[dict[str, Any]], **kwargs: Any) -> str:
    """Synchronous chat completion. Returns assistant content."""
    client = get_client()
    s = get_settings()
    resp = client.chat.completions.create(
        model=kwargs.pop("model", s.llm_model_name),
        messages=messages,  # type: ignore[arg-type]
        **kwargs,
    )
    return resp.choices[0].message.content or ""


def chat_json(messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    """Chat completion forced to JSON. Returns parsed dict."""
    import json

    raw = chat(messages, response_format={"type": "json_object"}, **kwargs)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned non-JSON: {raw[:200]!r}") from exc


__all__ = ["chat", "chat_json", "get_client"]
