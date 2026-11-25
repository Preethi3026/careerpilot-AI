"""Compatibility helper for existing callers, backed by Ollama's HTTP API."""

from __future__ import annotations

from typing import Any

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.core.ollama_client import ollama_client


def get_ai_response(
    message: str,
    *,
    think: bool = False,
    timeout: float = 120,
    format: dict[str, Any] | str | None = None,
    num_predict: int | None = None,
    num_ctx: int | None = None,
    keep_alive: str | int | None = "5m",
    tools: list[dict[str, Any]] | None = None,
) -> str:
    response = ollama_client.chat(
        [{"role": "user", "content": message}],
        format=format,
        think=think,
        timeout=timeout,
        num_predict=num_predict,
        num_ctx=num_ctx,
        keep_alive=keep_alive,
        tools=tools,
    )
    return str(response.get("message", {}).get("content", ""))


class _LegacyLLM:
    """Keep the prior ``llm.invoke`` interface for any downstream integrations."""

    def invoke(self, message: str) -> Any:
        return type("OllamaMessage", (), {"content": get_ai_response(message)})()


llm = _LegacyLLM()
