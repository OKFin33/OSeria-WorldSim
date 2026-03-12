"""Parallel pack customization against a frozen compile package."""

from __future__ import annotations

import asyncio

from .common import PROMPTS_DIR, dump_json, load_text
from .conductor import ForgeManifest, ForgeTask
from .domain import ForgeContext
from .llm_client import LLMClientProtocol

NO_TEMPLATE_FALLBACK = "此维度没有现成的规则模板。请根据编译后的世界简报和玩家侧写，从零创建一套规则。"


class Forge:
    def __init__(self, llm_client: LLMClientProtocol, *, prompt_path: str | None = None) -> None:
        self.llm = llm_client
        self.prompt_template = load_text(prompt_path or PROMPTS_DIR / "subagent_system_prompt.md")

    async def _forge_single_module(self, task: ForgeTask, compile_output_briefing: str, compile_output_profile: str, forge_context: ForgeContext) -> str:
        supplementary = "\n\n".join(task.supplementary_packs) if task.supplementary_packs else "无"
        pack_content = task.pack_content or NO_TEMPLATE_FALLBACK
        system_prompt = self.prompt_template.format(
            module_name=task.pack_id or task.dimension,
            narrative_briefing=compile_output_briefing,
            player_profile=compile_output_profile,
            pack_content=pack_content,
            supplementary_packs=supplementary,
        )
        user_msg = (
            "请直接输出定制后的规则段落，无需闲聊和过度解释。\n"
            "以下是冻结后的世界 flavor context，仅供你贴合这次用户：\n"
            f"{dump_json(forge_context.to_dict())}"
        )
        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_msg=user_msg,
            temperature=0.7,
        )
        return f"### [{task.dimension}]\n{response.strip()}"

    async def execute(self, manifest: ForgeManifest, forge_context: ForgeContext) -> dict[str, str]:
        if not manifest.tasks:
            return {}

        briefing = manifest.compile_output.narrative_briefing
        profile = manifest.compile_output.player_profile
        results = await asyncio.gather(
            *(
                self._forge_single_module(task, briefing, profile, forge_context)
                for task in manifest.tasks
            )
        )
        return {manifest.tasks[index].dimension: results[index] for index in range(len(results))}
