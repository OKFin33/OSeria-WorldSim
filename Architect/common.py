"""Shared utilities for the Architect runtime."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ARCHITECT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ARCHITECT_ROOT.parent
DATA_DIR = ARCHITECT_ROOT / "data"
PROMPTS_DIR = ARCHITECT_ROOT / "prompts"

OPENING_QUESTION = (
    "闭上眼。在这个为你准备的世界里，你想在推开窗后看到怎样的景象？"
    "是飞剑划破云霄，是霓虹闪烁的未来都市，是魔法塔尖的星光，"
    "还是现代社会里的另一种可能？随意描述你脑海中的第一幕画卷。"
)


def load_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(load_text(path))


def dump_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def extract_tagged_block(text: str, start_tag: str, end_tag: str) -> str | None:
    start = text.find(start_tag)
    if start == -1:
        return None
    start += len(start_tag)
    end = text.find(end_tag, start)
    if end == -1:
        return None
    return text[start:end].strip()


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


def load_dotenv(env_path: str | Path | None = None) -> None:
    candidates = [Path(env_path)] if env_path else [PROJECT_ROOT / ".env", ARCHITECT_ROOT / ".env"]
    for candidate in candidates:
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
        return

