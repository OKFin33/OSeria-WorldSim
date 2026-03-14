"""Parallel module customization against a frozen compile package."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from .common import PROMPTS_DIR, dump_json, load_text
from .conductor import ForgeManifest, ForgeMode, ForgeTask
from .domain import ForgeContext
from .llm_client import LLMClientProtocol

NO_TEMPLATE_FALLBACK = "此模块没有现成模板。请只围绕该模块职责，为当前世界补出最小可用规则。"


@dataclass
class ForgeExecution:
    module_id: str
    forge_mode: ForgeMode
    section: str
    dimension: str | None
    pack_id: str | None
    llm_invoked: bool
    rendered_content: str
    supplementary_pack_ids: list[str]
    elapsed_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "module_id": self.module_id,
            "forge_mode": self.forge_mode,
            "section": self.section,
            "dimension": self.dimension,
            "pack_id": self.pack_id,
            "llm_invoked": self.llm_invoked,
            "supplementary_pack_ids": list(self.supplementary_pack_ids),
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass
class ForgeExecutionResult:
    rendered_modules: dict[str, str]
    executions: list[ForgeExecution]

    @property
    def llm_elapsed_ms(self) -> int:
        return sum(execution.elapsed_ms for execution in self.executions if execution.llm_invoked)


class Forge:
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        *,
        soft_prompt_path: str | None = None,
        full_prompt_path: str | None = None,
    ) -> None:
        self.llm = llm_client
        self.soft_prompt_template = load_text(soft_prompt_path or PROMPTS_DIR / "soft_forge_system_prompt.md")
        self.full_prompt_template = load_text(full_prompt_path or PROMPTS_DIR / "full_forge_system_prompt.md")

    async def _forge_task(
        self,
        task: ForgeTask,
        *,
        narrative_briefing: str,
        player_profile: str,
        forge_context: ForgeContext,
    ) -> ForgeExecution:
        started = time.perf_counter()
        if task.forge_mode in {"locked", "parameterized"}:
            return ForgeExecution(
                module_id=task.module_id,
                forge_mode=task.forge_mode,
                section=task.section,
                dimension=task.dimension,
                pack_id=task.pack_id,
                llm_invoked=False,
                rendered_content=task.source_content,
                supplementary_pack_ids=list(task.supplementary_pack_ids),
                elapsed_ms=int((time.perf_counter() - started) * 1000),
            )

        supplementary = "\n\n".join(task.supplementary_packs) if task.supplementary_packs else "无"
        prompt_template = (
            self.soft_prompt_template if task.forge_mode == "soft_forged" else self.full_prompt_template
        )
        system_prompt = prompt_template.format(
            module_name=task.module_id,
            module_scope=task.module_scope,
            rewrite_budget=task.rewrite_budget,
            narrative_briefing=narrative_briefing,
            player_profile=player_profile,
            source_content=task.source_content or NO_TEMPLATE_FALLBACK,
            supplementary_packs=supplementary,
            dimension=task.dimension or "core",
        )
        user_msg = (
            "请直接输出该模块最终要进入系统提示词的正文，不要输出 JSON，不要加代码块，不要补额外说明。\n"
            "以下是冻结后的世界 flavor context，仅供你对齐语感与细节：\n"
            f"{dump_json(forge_context.to_dict())}"
        )
        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_msg=user_msg,
            temperature=0.6 if task.forge_mode == "soft_forged" else 0.7,
        )
        return ForgeExecution(
            module_id=task.module_id,
            forge_mode=task.forge_mode,
            section=task.section,
            dimension=task.dimension,
            pack_id=task.pack_id,
            llm_invoked=True,
            rendered_content=response.strip(),
            supplementary_pack_ids=list(task.supplementary_pack_ids),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )

    async def execute(self, manifest: ForgeManifest, forge_context: ForgeContext) -> ForgeExecutionResult:
        if not manifest.tasks:
            return ForgeExecutionResult(rendered_modules={}, executions=[])

        briefing = manifest.compile_output.narrative_briefing
        profile = manifest.compile_output.player_profile
        executions = await asyncio.gather(
            *(
                self._forge_task(
                    task,
                    narrative_briefing=briefing,
                    player_profile=profile,
                    forge_context=forge_context,
                )
                for task in manifest.tasks
            )
        )
        return ForgeExecutionResult(
            rendered_modules={execution.module_id: execution.rendered_content for execution in executions},
            executions=list(executions),
        )
