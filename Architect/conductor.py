"""Compile-output driven pack routing for Forge."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .common import DATA_DIR, load_json, load_text
from .domain import CompileOutput


@dataclass
class ForgeTask:
    dimension: str
    pack_id: str | None
    pack_content: str
    supplementary_packs: list[str]


@dataclass
class ForgeManifest:
    tasks: list[ForgeTask]
    emergent_dimensions: list[str]
    excluded_dimensions: list[str]
    compile_output: CompileOutput


class Conductor:
    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.dimension_map = load_json(self.data_dir / "dimension_map.json")
        self.pack_registry = self._build_pack_registry()

    def _build_pack_registry(self) -> dict[str, str]:
        registry: dict[str, str] = {}
        packs_dir = self.data_dir / "packs"
        for pack_path in sorted(packs_dir.glob("*.json")):
            payload = load_json(pack_path)
            module_id = str(payload.get("module_id", "")).strip()
            if module_id:
                registry[module_id] = load_text(pack_path)
        return registry

    def _load_pack_content(self, pack_id: str) -> str:
        return self.pack_registry.get(pack_id, "")

    def _resolve_all_packs(self, dim: str, all_confirmed: set[str]) -> tuple[str | None, str, list[str]]:
        entry = self.dimension_map.get(dim)
        if not entry:
            return None, "", []

        primary_id = entry.get("primary")
        primary_content = self._load_pack_content(primary_id) if primary_id else ""

        supplementary: list[str] = []
        included_pack_ids: set[str] = set()

        for required_pack in entry.get("requires", []):
            content = self._load_pack_content(required_pack)
            if content and required_pack not in included_pack_ids:
                supplementary.append(content)
                included_pack_ids.add(required_pack)

        for consider_pack in entry.get("also_consider", []):
            already_primary_elsewhere = any(
                self.dimension_map.get(other_dim, {}).get("primary") == consider_pack
                for other_dim in all_confirmed
                if other_dim != dim
            )
            if already_primary_elsewhere or consider_pack in included_pack_ids:
                continue
            content = self._load_pack_content(consider_pack)
            if content:
                supplementary.append(content)
                included_pack_ids.add(consider_pack)

        return primary_id, primary_content, supplementary

    def build_manifest(self, compile_output: CompileOutput) -> ForgeManifest:
        confirmed = list(dict.fromkeys(compile_output.confirmed_dimensions))
        confirmed_set = set(confirmed)
        tasks: list[ForgeTask] = []
        for dimension in confirmed:
            pack_id, pack_content, supplementary = self._resolve_all_packs(dimension, confirmed_set)
            tasks.append(
                ForgeTask(
                    dimension=dimension,
                    pack_id=pack_id,
                    pack_content=pack_content,
                    supplementary_packs=supplementary,
                )
            )

        return ForgeManifest(
            tasks=tasks,
            emergent_dimensions=list(compile_output.emergent_dimensions),
            excluded_dimensions=list(compile_output.excluded_dimensions),
            compile_output=compile_output,
        )
