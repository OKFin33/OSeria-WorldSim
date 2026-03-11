"""Layer 3 Assembler: stitch the final system prompt."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import DATA_DIR, load_json
from .conductor import ForgeManifest
from .llm_client import LLMClientProtocol

CORE_FILES = {
    "system_role": ["meta.role.json"],
    "experience": ["meta.experience.json"],
    "constitution": ["constitution.law1.json", "constitution.law2.json", "constitution.law3.json"],
    "engine": [
        "eng.sensory.json",
        "eng.physics.json",
        "eng.casting.json",
        "eng.entropy.json",
        "eng.pacing.json",
        "eng.subtext.json",
        "eng.veil.json",
        "eng.archivist.json",
    ],
}

DEFAULT_CORE_VARIABLES = {
    "tone_primary": "写实",
    "tone_secondary": "感伤",
    "content_ceiling": "PG-13",
    "humor_density": "偶尔点缀",
    "sensory_smell_example": "雨后混着金属味的空气",
    "sensory_sound_example": "远处持续不断的低频轰鸣",
    "tone_filter": "压抑而克制",
    "ignorance_reaction": "Fear",
}


class Assembler:
    def __init__(self, llm_client: LLMClientProtocol, *, data_dir: str | Path | None = None) -> None:
        self.llm = llm_client
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR

    async def assemble(self, forged_results: dict[str, str], manifest: ForgeManifest) -> str:
        variables = await self._extract_core_variables(
            briefing=manifest.narrative_briefing,
            profile=manifest.player_profile,
        )

        output = [
            "# OSeria System Prompt - Customized World",
            "## I. System Role",
            self._load_core_content("meta.role.json", variables),
            "## II. Experience Standard",
            self._load_core_content("meta.experience.json", variables),
            "## III. Immutable Constitution",
        ]

        output.extend(self._load_core_content(filename, variables) for filename in CORE_FILES["constitution"])
        output.append("## IV. Engine Protocols")
        output.extend(self._load_core_content(filename, variables) for filename in CORE_FILES["engine"])

        output.append("## V. World-Specific Rules")
        if forged_results:
            for task in manifest.tasks:
                output.append(forged_results[task.dimension])
        else:
            output.append("No pre-forged rules were generated. The world remains mostly emergent.")

        output.append("## VI. Emergent Dimensions")
        if manifest.emergent_dimensions:
            output.append("以下维度未预写规则，由运行时自然涌现：")
            output.extend(f"- {dimension}" for dimension in manifest.emergent_dimensions)
        else:
            output.append("无。")

        output.append("## VII. Player Calibration")
        output.append(manifest.player_profile)

        return "\n\n".join(output)

    async def _extract_core_variables(self, *, briefing: str, profile: str) -> dict[str, str]:
        prompt = (
            "基于以下世界简报和玩家侧写，提取 8 个关键设定变量并返回 JSON。\n"
            f"世界简报：{briefing}\n"
            f"玩家侧写：{profile}\n"
            "字段要求：tone_primary, tone_secondary, content_ceiling, humor_density, "
            "sensory_smell_example, sensory_sound_example, tone_filter, ignorance_reaction。"
        )
        payload = await self.llm.generate_json(
            prompt,
            system_prompt="你是结构化信息提取器。只返回 JSON 对象。",
            temperature=0.2,
        )

        variables = dict(DEFAULT_CORE_VARIABLES)
        for key in DEFAULT_CORE_VARIABLES:
            value = str(payload.get(key, "")).strip()
            if value:
                variables[key] = value
        return variables

    def _load_core_content(self, filename: str, variables: dict[str, str]) -> str:
        payload = load_json(self.data_dir / "core" / filename)
        content = str(payload.get("content", "")).strip()
        for key, value in variables.items():
            content = re.sub(r"\{\{\s*" + re.escape(key) + r"\s*\}\}", value, content)
        return content

