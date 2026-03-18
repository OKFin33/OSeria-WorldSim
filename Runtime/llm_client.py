"""Async LLM client with OpenAI-compatible chat completions support."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator, Protocol
from urllib import error, request

from .common import load_dotenv


class LLMClientProtocol(Protocol):
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        response_format: str | None = None,
    ) -> str:
        ...

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        ...

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        response_format: str | None = None,
    ) -> AsyncIterator[str]:
        ...


def extract_first_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response.")

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : index + 1])
    raise ValueError("Unterminated JSON object in model response.")


@dataclass
class OpenAICompatibleLLMClient:
    model: str
    api_key: str
    base_url: str
    timeout: float = 75.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "OpenAICompatibleLLMClient":
        load_dotenv()
        api_key = (
            os.getenv("RUNTIME_LLM_API_KEY")
            or os.getenv("ARCHITECT_LLM_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        base_url = (
            os.getenv("RUNTIME_LLM_BASE_URL")
            or os.getenv("ARCHITECT_LLM_BASE_URL")
            or os.getenv("DEEPSEEK_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        )
        model = (
            os.getenv("RUNTIME_LLM_MODEL")
            or os.getenv("ARCHITECT_LLM_MODEL")
            or os.getenv("DEEPSEEK_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "deepseek-chat"
        )
        if not api_key:
            raise ValueError("Missing API key. Set RUNTIME_LLM_API_KEY, ARCHITECT_LLM_API_KEY, or OPENAI_API_KEY.")
        timeout = float(os.getenv("RUNTIME_LLM_TIMEOUT_SECONDS", "75"))
        return cls(model=model, api_key=api_key, base_url=base_url.rstrip("/"), timeout=timeout)

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        response_format: str | None = None,
    ) -> str:
        payload_messages = list(messages)
        if system_prompt:
            payload_messages = [{"role": "system", "content": system_prompt}, *payload_messages]

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
        }
        if response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}

        raw_response = await self._post_with_retries(payload)
        choices = raw_response.get("choices") or []
        if not choices:
            raise RuntimeError("LLM response did not include any choices.")

        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            return "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ).strip()
        if not isinstance(content, str):
            raise RuntimeError("LLM response content format is unsupported.")
        return content.strip()

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        raw = await self.chat(
            [{"role": "user", "content": prompt}],
            system_prompt=system_prompt
            or "Return exactly one JSON object. No prose, no markdown fences.",
            temperature=temperature,
            response_format="json_object",
        )
        return extract_first_json_object(raw)

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        response_format: str | None = None,
    ) -> AsyncIterator[str]:
        payload_messages = list(messages)
        if system_prompt:
            payload_messages = [{"role": "system", "content": system_prompt}, *payload_messages]

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "stream": True,
        }
        if response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[object] = asyncio.Queue()
        sentinel = object()

        def pump() -> None:
            try:
                for chunk in self._post_json_stream(payload):
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop).result()
            except Exception as exc:  # pragma: no cover
                asyncio.run_coroutine_threadsafe(queue.put(exc), loop).result()
            finally:  # pragma: no cover
                asyncio.run_coroutine_threadsafe(queue.put(sentinel), loop).result()

        producer = asyncio.create_task(asyncio.to_thread(pump))
        try:
            while True:
                item = await queue.get()
                if item is sentinel:
                    break
                if isinstance(item, Exception):
                    raise item
                yield str(item)
            await producer
        finally:
            if not producer.done():
                producer.cancel()

    async def _post_with_retries(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return await asyncio.to_thread(self._post_json, payload)
            except Exception as exc:  # pragma: no cover
                last_error = exc
                if attempt >= self.max_retries:
                    break
                await asyncio.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"LLM request failed after retries: {last_error}") from last_error

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        req = request.Request(endpoint, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} from model API: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Network error while calling model API: {exc.reason}") from exc

    def _post_json_stream(self, payload: dict[str, Any]):
        body = json.dumps(payload).encode("utf-8")
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        req = request.Request(endpoint, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    event = json.loads(data)
                    choices = event.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {}) or {}
                    content = delta.get("content", "")
                    if isinstance(content, list):
                        content = "".join(
                            part.get("text", "")
                            for part in content
                            if isinstance(part, dict) and part.get("type") == "text"
                        )
                    if isinstance(content, str) and content:
                        yield content
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} from model API: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Network error while calling model API: {exc.reason}") from exc
