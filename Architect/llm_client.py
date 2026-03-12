"""Async LLM client with OpenAI-compatible chat completions support."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib import error, request

from .common import extract_first_json_object, load_dotenv


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

    async def generate(
        self,
        *,
        system_prompt: str,
        user_msg: str,
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


@dataclass
class OpenAICompatibleLLMClient:
    model: str
    api_key: str
    base_url: str
    timeout: float = 45.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "OpenAICompatibleLLMClient":
        load_dotenv()
        api_key = (
            os.getenv("ARCHITECT_LLM_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        base_url = (
            os.getenv("ARCHITECT_LLM_BASE_URL")
            or os.getenv("DEEPSEEK_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        )
        model = (
            os.getenv("ARCHITECT_LLM_MODEL")
            or os.getenv("DEEPSEEK_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "deepseek-chat"
        )
        if not api_key:
            raise ValueError("Missing API key. Set ARCHITECT_LLM_API_KEY or OPENAI_API_KEY.")
        return cls(model=model, api_key=api_key, base_url=base_url.rstrip("/"))

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

    async def generate(
        self,
        *,
        system_prompt: str,
        user_msg: str,
        temperature: float = 0.7,
        response_format: str | None = None,
    ) -> str:
        return await self.chat(
            [{"role": "user", "content": user_msg}],
            system_prompt=system_prompt,
            temperature=temperature,
            response_format=response_format,
        )

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        raw = await self.generate(
            system_prompt=system_prompt
            or "Return exactly one JSON object. No prose, no markdown fences.",
            user_msg=prompt,
            temperature=temperature,
            response_format="json_object",
        )
        return extract_first_json_object(raw)

    async def _post_with_retries(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return await asyncio.to_thread(self._post_json, payload)
            except Exception as exc:  # pragma: no cover - exercised only on live API failure
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

