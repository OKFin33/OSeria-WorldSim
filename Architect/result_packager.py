"""Convert raw generation outputs into product-facing blueprint summaries."""

from __future__ import annotations

import re

from .api_models import BlueprintSummary, ForgeModuleSummary
from .conductor import ForgeManifest
from .interviewer import InterviewArtifacts

_KEYWORD_BANK = [
    "写实",
    "压抑",
    "轻松",
    "暗黑",
    "幽默",
    "冷硬",
    "权谋",
    "都市",
    "修仙",
    "浪漫",
    "克制",
    "阶层",
    "成长",
    "冒险",
]


class ResultPackager:
    def build_blueprint_summary(
        self,
        *,
        artifacts: InterviewArtifacts,
        manifest: ForgeManifest,
        system_prompt: str,
    ) -> BlueprintSummary:
        world_summary = self._normalize_text(artifacts.narrative_briefing)
        protagonist_hook = self._extract_protagonist_hook(world_summary)
        core_tension = self._extract_core_tension(world_summary)
        title = self._derive_title(world_summary, protagonist_hook, core_tension)
        tone_keywords = self._extract_tone_keywords(world_summary, artifacts.player_profile)

        return BlueprintSummary(
            title=title,
            world_summary=world_summary,
            protagonist_hook=protagonist_hook,
            core_tension=core_tension,
            tone_keywords=tone_keywords,
            player_profile=self._normalize_text(artifacts.player_profile),
            confirmed_dimensions=list(artifacts.routing_tags.get("confirmed_dimensions", [])),
            emergent_dimensions=list(artifacts.routing_tags.get("emergent_dimensions", [])),
            forged_modules=[
                ForgeModuleSummary(dimension=task.dimension, pack_id=task.pack_id)
                for task in manifest.tasks
            ],
        )

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _split_sentences(self, text: str) -> list[str]:
        chunks = re.split(r"(?<=[。！？!?])\s*", text)
        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def _extract_protagonist_hook(self, summary: str) -> str:
        for sentence in self._split_sentences(summary):
            if any(token in sentence for token in ("主角", "你", "他", "她", "起步", "站在", "出身")):
                return sentence
        sentences = self._split_sentences(summary)
        return sentences[0] if sentences else "一个世界正在等待主角推门而入。"

    def _extract_core_tension(self, summary: str) -> str:
        for sentence in self._split_sentences(summary):
            if any(token in sentence for token in ("张力", "冲突", "对抗", "秩序", "资源", "攀爬", "代价")):
                return sentence
        sentences = self._split_sentences(summary)
        if len(sentences) > 1:
            return sentences[1]
        return sentences[0] if sentences else "世界的核心张力仍在等待被命名。"

    def _derive_title(self, world_summary: str, protagonist_hook: str, core_tension: str) -> str:
        base = protagonist_hook or core_tension or world_summary
        cleaned = re.sub(r"[，。！？、：；,.!?\\s]+", "", base)
        if not cleaned:
            return "定制世界"
        if len(cleaned) <= 12:
            return cleaned
        return f"{cleaned[:12]}..."

    def _extract_tone_keywords(self, world_summary: str, player_profile: str) -> list[str]:
        source = f"{world_summary} {player_profile}"
        selected = [keyword for keyword in _KEYWORD_BANK if keyword in source]
        if selected:
            return selected[:5]

        fallback = []
        if "不" in player_profile or "压" in world_summary:
            fallback.append("压抑")
        if "慢" in player_profile:
            fallback.append("克制")
        if "城" in world_summary or "都市" in world_summary:
            fallback.append("都市")
        if "成长" in world_summary or "向上" in world_summary:
            fallback.append("成长")
        return fallback[:5] or ["写实", "克制"]

