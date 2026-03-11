"""
Conductor (Layer 1) — 最终 Routing 确认与维度映射

职责：
1. 接收访谈员的三大交付物（Routing Tags, Narrative Briefing, Player Profile）
2. 读取 dimension_map.json，将抽象的体验维度映射为具体的 Pack 内容
3. 处理 1:N 映射（also_consider / requires）和 LLM 自建的未知维度
4. 生成 ForgeManifest，交由 Layer 2 Forge 初始化 SubAgents
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import DATA_DIR, load_json, load_text


@dataclass
class ForgeTask:
    """单个 SubAgent 的任务配置"""

    dimension: str
    pack_id: str | None
    pack_content: str
    supplementary_packs: list[str]
    narrative_briefing: str
    player_profile: str


@dataclass
class ForgeManifest:
    """交接给 Forge 的完整任务清单"""

    tasks: list[ForgeTask]
    emergent_dimensions: list[str]
    excluded_dimensions: list[str]
    narrative_briefing: str
    player_profile: str


CORE_VARIABLE_FILES = [
    "core/meta.experience.json",
    "core/eng.sensory.json",
    "core/eng.veil.json",
]


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
            module_id = payload.get("module_id")
            if module_id:
                registry[module_id] = load_text(pack_path)
        return registry

    def _load_pack_content(self, pack_id: str) -> str:
        """通过 pack 模块自身的 module_id 取内容，避免猜文件名。"""
        return self.pack_registry.get(pack_id, "")

    def _resolve_all_packs(self, dim: str, all_confirmed: set[str]) -> tuple[str | None, str, list[str]]:
        """
        解析一个维度需要加载的所有 Pack。

        返回: (primary_pack_id, primary_content, supplementary_contents)
        """
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

    def process_interview_results(
        self,
        routing_tags: dict[str, Any],
        narrative_briefing: str,
        player_profile: str,
    ) -> ForgeManifest:
        confirmed = list(dict.fromkeys(routing_tags.get("confirmed_dimensions", [])))
        emergent = list(dict.fromkeys(routing_tags.get("emergent_dimensions", [])))
        excluded = list(dict.fromkeys(routing_tags.get("excluded_dimensions", [])))
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
                    narrative_briefing=narrative_briefing,
                    player_profile=player_profile,
                )
            )

        return ForgeManifest(
            tasks=tasks,
            emergent_dimensions=emergent,
            excluded_dimensions=excluded,
            narrative_briefing=narrative_briefing,
            player_profile=player_profile,
        )
