"""Compile-output driven module routing for Forge."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .common import DATA_DIR, load_json
from .domain import CompileOutput

SectionName = Literal["meta", "constitution", "engine", "world_rules"]
ForgeMode = Literal["locked", "parameterized", "soft_forged", "full_forged"]
RewriteBudget = Literal["none", "low", "high"]

CORE_MODULE_FILES: list[tuple[SectionName, str]] = [
    ("meta", "meta.role.json"),
    ("meta", "meta.experience.json"),
    ("constitution", "constitution.law1.json"),
    ("constitution", "constitution.law2.json"),
    ("constitution", "constitution.law3.json"),
    ("engine", "eng.sensory.json"),
    ("engine", "eng.physics.json"),
    ("engine", "eng.casting.json"),
    ("engine", "eng.entropy.json"),
    ("engine", "eng.pacing.json"),
    ("engine", "eng.subtext.json"),
    ("engine", "eng.veil.json"),
    ("engine", "eng.archivist.json"),
]


@dataclass
class ForgeTask:
    module_id: str
    section: SectionName
    forge_mode: ForgeMode
    source_content: str
    dimension: str | None
    pack_id: str | None
    supplementary_packs: list[str]
    supplementary_pack_ids: list[str]
    module_scope: str
    rewrite_budget: RewriteBudget


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
        self.core_registry = self._build_core_registry()
        self.pack_registry = self._build_pack_registry()

    def _build_core_registry(self) -> dict[str, dict[str, Any]]:
        registry: dict[str, dict[str, Any]] = {}
        core_dir = self.data_dir / "core"
        for filename in dict.fromkeys(filename for _, filename in CORE_MODULE_FILES):
            payload = load_json(core_dir / filename)
            module_id = str(payload.get("module_id", "")).strip()
            if module_id:
                registry[module_id] = payload
        return registry

    def _build_pack_registry(self) -> dict[str, dict[str, Any]]:
        registry: dict[str, dict[str, Any]] = {}
        packs_dir = self.data_dir / "packs"
        for pack_path in sorted(packs_dir.glob("*.json")):
            payload = load_json(pack_path)
            module_id = str(payload.get("module_id", "")).strip()
            if module_id:
                registry[module_id] = payload
        return registry

    def _load_pack_payload(self, pack_id: str) -> dict[str, Any] | None:
        return self.pack_registry.get(pack_id)

    def _resolve_all_packs(
        self, dim: str, all_confirmed: set[str]
    ) -> tuple[str | None, str, list[str], list[str], dict[str, Any] | None]:
        entry = self.dimension_map.get(dim)
        if not entry:
            return None, "", [], [], None

        primary_id = entry.get("primary")
        primary_payload = self._load_pack_payload(primary_id) if primary_id else None
        primary_content = str((primary_payload or {}).get("content", "")).strip()

        supplementary: list[str] = []
        supplementary_ids: list[str] = []
        included_pack_ids: set[str] = set()

        for required_pack in entry.get("requires", []):
            content = str((self._load_pack_payload(required_pack) or {}).get("content", "")).strip()
            if content and required_pack not in included_pack_ids:
                supplementary.append(content)
                supplementary_ids.append(required_pack)
                included_pack_ids.add(required_pack)

        for consider_pack in entry.get("also_consider", []):
            already_primary_elsewhere = any(
                self.dimension_map.get(other_dim, {}).get("primary") == consider_pack
                for other_dim in all_confirmed
                if other_dim != dim
            )
            if already_primary_elsewhere or consider_pack in included_pack_ids:
                continue
            content = str((self._load_pack_payload(consider_pack) or {}).get("content", "")).strip()
            if content:
                supplementary.append(content)
                supplementary_ids.append(consider_pack)
                included_pack_ids.add(consider_pack)

        return primary_id, primary_content, supplementary, supplementary_ids, primary_payload

    def _build_core_task(self, section: SectionName, filename: str) -> ForgeTask:
        payload = load_json(self.data_dir / "core" / filename)
        return ForgeTask(
            module_id=str(payload["module_id"]),
            section=section,
            forge_mode=str(payload["forge_mode"]),
            source_content=str(payload.get("content", "")).strip(),
            dimension=None,
            pack_id=None,
            supplementary_packs=[],
            supplementary_pack_ids=[],
            module_scope=str(payload.get("module_scope", "")).strip(),
            rewrite_budget=str(payload.get("rewrite_budget", "none")),
        )

    def _build_world_rule_task(self, dimension: str, all_confirmed: set[str]) -> ForgeTask:
        pack_id, pack_content, supplementary, supplementary_ids, payload = self._resolve_all_packs(
            dimension, all_confirmed
        )
        if payload is None:
            return ForgeTask(
                module_id=dimension,
                section="world_rules",
                forge_mode="full_forged",
                source_content=pack_content,
                dimension=dimension,
                pack_id=None,
                supplementary_packs=supplementary,
                supplementary_pack_ids=supplementary_ids,
                module_scope="只为该 confirmed dimension 编写对应的世界规则，不要扩写其他模块职责。",
                rewrite_budget="high",
            )
        return ForgeTask(
            module_id=str(payload["module_id"]),
            section="world_rules",
            forge_mode=str(payload["forge_mode"]),
            source_content=pack_content,
            dimension=dimension,
            pack_id=pack_id,
            supplementary_packs=supplementary,
            supplementary_pack_ids=supplementary_ids,
            module_scope=str(payload.get("module_scope", "")).strip(),
            rewrite_budget=str(payload.get("rewrite_budget", "high")),
        )

    def build_manifest(self, compile_output: CompileOutput) -> ForgeManifest:
        confirmed = list(dict.fromkeys(compile_output.confirmed_dimensions))
        confirmed_set = set(confirmed)
        tasks = [self._build_core_task(section, filename) for section, filename in CORE_MODULE_FILES]
        tasks.extend(self._build_world_rule_task(dimension, confirmed_set) for dimension in confirmed)

        return ForgeManifest(
            tasks=tasks,
            emergent_dimensions=list(compile_output.emergent_dimensions),
            excluded_dimensions=list(compile_output.excluded_dimensions),
            compile_output=compile_output,
        )
