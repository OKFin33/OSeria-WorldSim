"""Layer 3 Assembler: stitch the final system prompt from frozen inputs."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from .common import dump_json
from .conductor import ForgeManifest, ForgeTask
from .domain import AssemblerContext, CompileOutput
from .forge import ForgeExecutionResult
from .llm_client import LLMClientProtocol

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

FINAL_TITLE = "# OSeria System Prompt - Customized World"


@dataclass
class AssemblerDebugInfo:
    extract_core_variables_elapsed_ms: int
    total_elapsed_ms: int

    def to_dict(self) -> dict[str, int]:
        return {
            "extract_core_variables_elapsed_ms": self.extract_core_variables_elapsed_ms,
            "total_elapsed_ms": self.total_elapsed_ms,
        }


class Assembler:
    def __init__(self, llm_client: LLMClientProtocol, *, data_dir: str | Path | None = None) -> None:
        self.llm = llm_client
        self.data_dir = Path(data_dir) if data_dir else None
        self.last_debug_info = AssemblerDebugInfo(
            extract_core_variables_elapsed_ms=0,
            total_elapsed_ms=0,
        )

    async def assemble(
        self,
        forge_result: ForgeExecutionResult,
        manifest: ForgeManifest,
        assembler_context: AssemblerContext,
    ) -> str:
        started = time.perf_counter()
        compile_output = manifest.compile_output
        extract_started = time.perf_counter()
        variables = await self._extract_core_variables(
            compile_output=compile_output,
            assembler_context=assembler_context,
        )
        extract_elapsed_ms = int((time.perf_counter() - extract_started) * 1000)

        output = [
            FINAL_TITLE,
            "## I. System Role",
        ]
        output.extend(self._render_section(manifest, forge_result, variables, "meta", module_ids={"core.meta.role"}))
        output.append("## II. Experience Standard")
        output.extend(
            self._render_section(manifest, forge_result, variables, "meta", module_ids={"core.meta.experience"})
        )
        output.append("## III. Immutable Constitution")
        output.extend(self._render_section(manifest, forge_result, variables, "constitution"))
        output.append("## IV. Engine Protocols")
        output.extend(self._render_section(manifest, forge_result, variables, "engine"))
        output.append("## V. World-Specific Rules")
        world_rules = self._render_section(manifest, forge_result, variables, "world_rules")
        output.extend(world_rules or ["No pre-forged rules were generated. The world remains mostly emergent."])
        output.append("## VI. Emergent Dimensions")
        if compile_output.emergent_dimensions:
            output.append("以下维度未预写规则，由运行时自然涌现：")
            output.extend(f"- {dimension}" for dimension in compile_output.emergent_dimensions)
        else:
            output.append("无。")
        output.append("## VII. Player Calibration")
        output.append(compile_output.player_profile)
        final_prompt = "\n\n".join(part for part in output if part.strip())
        self.last_debug_info = AssemblerDebugInfo(
            extract_core_variables_elapsed_ms=extract_elapsed_ms,
            total_elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        return final_prompt

    async def _extract_core_variables(
        self,
        *,
        compile_output: CompileOutput,
        assembler_context: AssemblerContext,
    ) -> dict[str, str]:
        prompt = (
            "基于以下冻结输入，为 core/meta.experience 与 eng.* 提取 8 个关键变量。\n"
            f"CompileOutput:\n{dump_json(compile_output.to_dict())}\n\n"
            f"AssemblerContext:\n{dump_json(assembler_context.to_dict())}\n\n"
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

    def _render_section(
        self,
        manifest: ForgeManifest,
        forge_result: ForgeExecutionResult,
        variables: dict[str, str],
        section: str,
        *,
        module_ids: set[str] | None = None,
    ) -> list[str]:
        rendered: list[str] = []
        for task in manifest.tasks:
            if task.section != section:
                continue
            if module_ids is not None and task.module_id not in module_ids:
                continue
            content = self._render_task(task, forge_result, variables)
            if content:
                rendered.append(content)
        return rendered

    def _render_task(
        self,
        task: ForgeTask,
        forge_result: ForgeExecutionResult,
        variables: dict[str, str],
    ) -> str:
        if task.forge_mode in {"locked", "parameterized"}:
            content = self._render_template_variables(task.source_content, variables)
        else:
            content = forge_result.rendered_modules.get(task.module_id, task.source_content)
            content = self._render_template_variables(content, variables)
        return self._clean_module_output(content)

    def _render_template_variables(self, content: str, variables: dict[str, str]) -> str:
        rendered = content
        for key, value in variables.items():
            rendered = re.sub(r"\{\{\s*" + re.escape(key) + r"\s*\}\}", value, rendered)
        return rendered.strip()

    def _clean_module_output(self, content: str) -> str:
        cleaned = content.strip()
        if not cleaned:
            return ""
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned)
        json_match = re.match(r"^\s*\{.*\}\s*$", cleaned, re.DOTALL)
        if json_match:
            try:
                payload = json.loads(cleaned)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                content_value = payload.get("content")
                if isinstance(content_value, str):
                    cleaned = content_value.strip()
        if cleaned.startswith(FINAL_TITLE):
            cleaned = cleaned[len(FINAL_TITLE) :].strip()
        cleaned = re.sub(r"^##\s+(I|II|III|IV|V|VI|VII)\.\s+[^\n]+\n*", "", cleaned, count=1)
        return cleaned.strip()
