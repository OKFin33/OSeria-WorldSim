"""Explicit registry for interview dimensions and steering metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .common import DATA_DIR, load_json

REGISTRY_PATH = DATA_DIR / "interview_dimensions.json"
DIMENSION_MAP_PATH = DATA_DIR / "dimension_map.json"
PROMPT_DIMENSION_PLACEHOLDER = "{{INTERVIEW_DIMENSION_MENU}}"


@dataclass(frozen=True)
class SteeringWeights:
    natural_priority: int
    brief_priority: int
    reject_priority: int


@dataclass(frozen=True)
class InterviewDimension:
    id: str
    display_name: str
    cue_keywords: tuple[str, ...]
    prompt_summary: str
    bubble_prompts: tuple[str, ...]
    steering: SteeringWeights


class InterviewDimensionRegistry:
    def __init__(self, dimensions: list[InterviewDimension]) -> None:
        self.dimensions = dimensions
        self._by_id = {dimension.id: dimension for dimension in dimensions}
        self._order = {dimension.id: index for index, dimension in enumerate(dimensions)}
        self._dimension_map = load_json(DIMENSION_MAP_PATH)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "InterviewDimensionRegistry":
        payload = load_json(path or REGISTRY_PATH)
        raw_dimensions = payload.get("dimensions", [])
        dimensions = [cls._parse_dimension(item) for item in raw_dimensions]
        registry = cls(dimensions)
        registry._validate_dimension_map_coverage()
        return registry

    @staticmethod
    def _parse_dimension(payload: dict) -> InterviewDimension:
        steering = payload["steering"]
        return InterviewDimension(
            id=str(payload["id"]).strip(),
            display_name=str(payload["display_name"]).strip(),
            cue_keywords=tuple(str(item).strip() for item in payload.get("cue_keywords", []) if str(item).strip()),
            prompt_summary=str(payload["prompt_summary"]).strip(),
            bubble_prompts=tuple(
                str(item).strip() for item in payload.get("bubble_prompts", []) if str(item).strip()
            ),
            steering=SteeringWeights(
                natural_priority=int(steering["natural_priority"]),
                brief_priority=int(steering["brief_priority"]),
                reject_priority=int(steering["reject_priority"]),
            ),
        )

    def render_prompt_menu(self) -> str:
        lines = [
            "| 标签 ID | 体验方向 | 感知关键词 |",
            "|---|---|---|",
        ]
        for dimension in self.dimensions:
            keywords = "、".join(dimension.cue_keywords)
            lines.append(f"| `{dimension.id}` | {dimension.display_name} | {keywords} |")
        return "\n".join(lines)

    def inject_into_prompt(self, template: str) -> str:
        if PROMPT_DIMENSION_PLACEHOLDER not in template:
            raise ValueError("Prompt template is missing the interview dimension placeholder.")
        return template.replace(PROMPT_DIMENSION_PLACEHOLDER, self.render_prompt_menu())

    def sort_dimensions(self, dimensions: list[str], *, strategy: str) -> list[str]:
        key_name = f"{strategy}_priority"

        def sort_key(dimension_id: str) -> tuple[int, int, str]:
            dimension = self._by_id.get(dimension_id)
            if dimension is None:
                return (9999, 9999, dimension_id)
            return (
                getattr(dimension.steering, key_name),
                self._order.get(dimension_id, 9999),
                dimension_id,
            )

        unique = list(dict.fromkeys(dimensions))
        known = [dimension_id for dimension_id in unique if dimension_id in self._by_id]
        unknown = [dimension_id for dimension_id in unique if dimension_id not in self._by_id]
        return sorted(known, key=sort_key) + unknown

    def bubble_label_for_dimension(self, dimension_id: str) -> str | None:
        entry = self._dimension_map.get(dimension_id)
        if isinstance(entry, dict):
            fallback_context = str(entry.get("fallback_context", "")).strip()
            if fallback_context:
                return fallback_context
        dimension = self._by_id.get(dimension_id)
        if dimension is None:
            return None
        return dimension.prompt_summary or dimension.display_name

    def bubble_prompts_for_dimension(self, dimension_id: str, *, seed_text: str = "") -> list[str]:
        dimension = self._by_id.get(dimension_id)
        if dimension is None:
            label = self.bubble_label_for_dimension(dimension_id)
            return [label] if label else []

        prompts = list(dimension.bubble_prompts)
        if not prompts:
            label = self.bubble_label_for_dimension(dimension_id)
            return [label] if label else []

        offset = self._rotation_offset(seed_text, len(prompts))
        return prompts[offset:] + prompts[:offset]

    @staticmethod
    def _rotation_offset(seed_text: str, size: int) -> int:
        if size <= 0 or not seed_text:
            return 0
        return sum(ord(char) for char in seed_text) % size

    def _validate_dimension_map_coverage(self) -> None:
        missing = [dimension.id for dimension in self.dimensions if dimension.id not in self._dimension_map]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Interview dimension registry has no dimension_map entry for: {joined}")
