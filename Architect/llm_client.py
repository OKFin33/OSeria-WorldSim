"""Async LLM client with OpenAI-compatible chat completions support."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
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
        timeout: float | None = None,
        max_retries: int | None = None,
        observer: Callable[..., None] | None = None,
    ) -> str:
        ...

    async def generate(
        self,
        *,
        system_prompt: str,
        user_msg: str,
        temperature: float = 0.7,
        response_format: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        observer: Callable[..., None] | None = None,
    ) -> str:
        ...

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        timeout: float | None = None,
        max_retries: int | None = None,
        observer: Callable[..., None] | None = None,
    ) -> dict[str, Any]:
        ...


@dataclass
class OpenAICompatibleLLMClient:
    model: str
    api_key: str
    base_url: str
    timeout: float = 45.0
    max_retries: int = 2
    extra_payload: dict[str, Any] | None = None

    @classmethod
    def from_env(cls) -> "OpenAICompatibleLLMClient":
        return cls._from_env()

    @classmethod
    def from_prefixed_env(
        cls,
        prefix: str,
        *,
        fallback_to_default: bool = False,
    ) -> "OpenAICompatibleLLMClient | None":
        return cls._from_env(prefix=prefix, fallback_to_default=fallback_to_default, optional=True)

    @classmethod
    def _from_env(
        cls,
        *,
        prefix: str | None = None,
        fallback_to_default: bool = True,
        optional: bool = False,
    ) -> "OpenAICompatibleLLMClient | None":
        load_dotenv()
        prefix_key = f"{prefix}_" if prefix else ""
        configured = any(
            os.getenv(f"{prefix_key}{name}") is not None
            for name in ("API_KEY", "BASE_URL", "MODEL", "ENABLE_THINKING")
        )
        if optional and prefix and not configured and not fallback_to_default:
            return None

        api_key = os.getenv(f"{prefix_key}API_KEY")
        base_url = os.getenv(f"{prefix_key}BASE_URL")
        model = os.getenv(f"{prefix_key}MODEL")
        enable_thinking_raw = os.getenv(f"{prefix_key}ENABLE_THINKING")

        if fallback_to_default or not prefix:
            api_key = (
                api_key
                or os.getenv("ARCHITECT_LLM_API_KEY")
                or os.getenv("DEEPSEEK_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            )
            base_url = (
                base_url
                or os.getenv("ARCHITECT_LLM_BASE_URL")
                or os.getenv("DEEPSEEK_BASE_URL")
                or os.getenv("OPENAI_BASE_URL")
                or "https://api.openai.com/v1"
            )
            model = (
                model
                or os.getenv("ARCHITECT_LLM_MODEL")
                or os.getenv("DEEPSEEK_MODEL")
                or os.getenv("OPENAI_MODEL")
                or "deepseek-chat"
            )
        else:
            base_url = base_url or "https://api.openai.com/v1"
            model = model or "deepseek-chat"

        if not api_key:
            raise ValueError("Missing API key. Set ARCHITECT_LLM_API_KEY or OPENAI_API_KEY.")

        extra_payload: dict[str, Any] | None = None
        if enable_thinking_raw is not None:
            extra_payload = {
                "enable_thinking": enable_thinking_raw.strip().lower()
                in {"1", "true", "yes", "on"}
            }

        return cls(
            model=model,
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            extra_payload=extra_payload,
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        response_format: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        observer: Callable[..., None] | None = None,
    ) -> str:
        payload_messages = list(messages)
        if system_prompt:
            payload_messages = [{"role": "system", "content": system_prompt}, *payload_messages]

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
        }
        if self.extra_payload:
            payload.update(self.extra_payload)
        if response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}

        raw_response = await self._post_with_retries(
            payload,
            timeout=timeout,
            max_retries=max_retries,
            observer=observer,
        )
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
        timeout: float | None = None,
        max_retries: int | None = None,
        observer: Callable[..., None] | None = None,
    ) -> str:
        return await self.chat(
            [{"role": "user", "content": user_msg}],
            system_prompt=system_prompt,
            temperature=temperature,
            response_format=response_format,
            timeout=timeout,
            max_retries=max_retries,
            observer=observer,
        )

    async def generate_json(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        timeout: float | None = None,
        max_retries: int | None = None,
        observer: Callable[..., None] | None = None,
    ) -> dict[str, Any]:
        raw = await self.generate(
            system_prompt=system_prompt
            or "Return exactly one JSON object. No prose, no markdown fences.",
            user_msg=prompt,
            temperature=temperature,
            response_format="json_object",
            timeout=timeout,
            max_retries=max_retries,
            observer=observer,
        )
        return extract_first_json_object(raw)

    async def _post_with_retries(
        self,
        payload: dict[str, Any],
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        observer: Callable[..., None] | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        effective_timeout = timeout if timeout is not None else self.timeout
        effective_max_retries = self.max_retries if max_retries is None else max_retries
        for attempt in range(effective_max_retries + 1):
            try:
                return await asyncio.to_thread(self._post_json, payload, effective_timeout)
            except Exception as exc:  # pragma: no cover - exercised only on live API failure
                last_error = exc
                if observer is not None:
                    observer(attempt=attempt + 1, error=exc)
                if attempt >= effective_max_retries:
                    break
                await asyncio.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"LLM request failed after retries: {last_error}") from last_error

    def _post_json(self, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        req = request.Request(endpoint, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} from model API: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Network error while calling model API: {exc.reason}") from exc
