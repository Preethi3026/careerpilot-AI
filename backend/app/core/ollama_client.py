"""Small direct client for Ollama's native /api/chat endpoint."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
import json
import os
from threading import Condition
from typing import Any

import httpx


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None, max_parallel: int = 2):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3:8b")
        self.max_parallel = max(1, max_parallel)
        self._condition = Condition()
        self._active = 0
        self._queue: list[object] = []

    @property
    def queue_position(self) -> int:
        """Number of requests waiting, useful to expose to the chat UI."""
        with self._condition:
            return len(self._queue)

    @contextmanager
    def _slot(self, on_queue: Callable[[int], None] | None = None):
        ticket = object()
        with self._condition:
            self._queue.append(ticket)
            while self._active >= self.max_parallel or self._queue[0] is not ticket:
                position = self._queue.index(ticket) + 1
                if on_queue:
                    try:
                        on_queue(position)
                    except Exception:
                        pass
                self._condition.wait(timeout=0.5)
            self._queue.remove(ticket)
            self._active += 1
            self._condition.notify_all()
        if on_queue:
            try:
                on_queue(0)
            except Exception:
                pass
        try:
            yield
        finally:
            with self._condition:
                self._active -= 1
                self._condition.notify_all()

    def _payload(
        self,
        messages: list[dict[str, Any]],
        *,
        format: dict[str, Any] | str | None,
        think: bool,
        num_predict: int | None,
        num_ctx: int | None,
        keep_alive: str | int | None,
        stream: bool,
        tools: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "think": think,
            "stream": stream,
            "options": {
                "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
                "num_predict": num_predict if num_predict is not None else int(os.getenv("OLLAMA_NUM_PREDICT", "4000")),
                "num_ctx": num_ctx if num_ctx is not None else int(os.getenv("OLLAMA_NUM_CTX", "8192")),
            },
        }
        if format is not None:
            payload["format"] = format
        if keep_alive is not None:
            payload["keep_alive"] = keep_alive
        if tools is not None:
            payload["tools"] = tools
        return payload

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        format: dict[str, Any] | str | None = None,
        think: bool = True,
        num_predict: int | None = None,
        num_ctx: int | None = None,
        keep_alive: str | int | None = "5m",
        stream: bool = False,
        tools: list[dict[str, Any]] | None = None,
        timeout: float = 900,
        on_queue: Callable[[int], None] | None = None,
    ) -> dict[str, Any] | Iterator[dict[str, Any]]:
        payload = self._payload(messages, format=format, think=think, num_predict=num_predict, num_ctx=num_ctx, keep_alive=keep_alive, stream=stream, tools=tools)
        if stream:
            return self._stream(payload, timeout, on_queue)
        with self._slot(on_queue):
            response = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()

    def _stream(self, payload: dict[str, Any], timeout: float, on_queue: Callable[[int], None] | None) -> Iterator[dict[str, Any]]:
        with self._slot(on_queue):
            with httpx.stream("POST", f"{self.base_url}/api/chat", json=payload, timeout=timeout) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.strip():
                        yield json.loads(line)


ollama_client = OllamaClient()
