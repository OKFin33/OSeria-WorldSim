"""Shared helpers for the Runtime module."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

RUNTIME_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = RUNTIME_ROOT.parent
PROMPTS_DIR = RUNTIME_ROOT / "prompts"
DEFAULT_SESSIONS_DIR = PROJECT_ROOT / ".runtime_sessions"


def load_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def dump_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def load_dotenv(env_path: str | Path | None = None) -> None:
    candidates = [Path(env_path)] if env_path else [PROJECT_ROOT / ".env", RUNTIME_ROOT / ".env"]
    for candidate in candidates:
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
