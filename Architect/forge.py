"""Layer 2 Forge: parallel pack customization."""

from __future__ import annotations

import asyncio

from .common import PROMPTS_DIR, load_text
from .conductor import ForgeManifest, ForgeTask
from .llm_client import LLMClientProtocol

NO_TEMPLATE_FALLBACK = "此维度没有现成的规则模板。请根据玩家的世界简报和侧写，从零创建一套规则。"


class Forge:
    def __init__(self, llm_client: LLMClientProtocol, *, prompt_path: str | None = None) -> None:
        self.llm = llm_client
        self.prompt_template = load_text(prompt_path or PROMPTS_DIR / "subagent_system_prompt.md")

    async def _forge_single_module(self, task: ForgeTask) -> str:
        supplementary = "\n\n".join(task.supplementary_packs) if task.supplementary_packs else "无"
        pack_content = task.pack_content or NO_TEMPLATE_FALLBACK
        system_prompt = self.prompt_template.format(
            module_name=task.pack_id or task.dimension,
            narrative_briefing=task.narrative_briefing,
            player_profile=task.player_profile,
            pack_content=pack_content,
            supplementary_packs=supplementary,
        )
        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_msg="请直接输出定制后的规则段落，无需闲聊和过度解释。",
            temperature=0.7,
        )
        return f"### [{task.dimension}]\n{response.strip()}"

    async def execute(self, manifest: ForgeManifest) -> dict[str, str]:
        if not manifest.tasks:
            return {}

        results = await asyncio.gather(*(self._forge_single_module(task) for task in manifest.tasks))
        return {manifest.tasks[index].dimension: results[index] for index in range(len(results))}

