"""Convert compile output into the product-facing blueprint."""

from __future__ import annotations

import re

from .api_models import BlueprintModel, ForgeModuleSummary
from .conductor import ForgeManifest
from .domain import CompileOutput

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

_SETTING_TOKENS = (
    "世界",
    "城市",
    "都市",
    "城",
    "镇",
    "小镇",
    "城邦",
    "海港",
    "港",
    "码头",
    "高墙",
    "雾",
    "霓虹",
    "学院",
    "王朝",
    "帝国",
    "荒原",
    "群岛",
    "边境",
)

_PERSONA_TOKENS = (
    "主角",
    "你",
    "他",
    "她",
    "起步",
    "站在",
    "出身",
    "奋斗者",
)


class ResultPackager:
    def build_blueprint(self, *, compile_output: CompileOutput, manifest: ForgeManifest) -> BlueprintModel:
        world_summary = self._normalize_text(compile_output.narrative_briefing)
        protagonist_hook = self._extract_world_entry(world_summary)
        core_tension = self._extract_core_tension(world_summary, protagonist_hook=protagonist_hook)
        title = self._derive_title(world_summary, protagonist_hook, core_tension)
        tone_keywords = self._extract_tone_keywords(world_summary, compile_output.player_profile)

        return BlueprintModel(
            title=title,
            world_summary=world_summary,
            protagonist_hook=protagonist_hook,
            core_tension=core_tension,
            tone_keywords=tone_keywords,
            player_profile=self._normalize_text(compile_output.player_profile),
            confirmed_dimensions=list(compile_output.confirmed_dimensions),
            emergent_dimensions=list(compile_output.emergent_dimensions),
            forged_modules=[
                ForgeModuleSummary(dimension=task.dimension, pack_id=task.pack_id)
                for task in manifest.tasks
                if task.section == "world_rules" and task.dimension is not None
            ],
        )

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _split_sentences(self, text: str) -> list[str]:
        chunks = re.split(r"(?<=[。！？!?])\s*", text)
        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def _extract_world_entry(self, summary: str) -> str:
        sentences = self._split_sentences(summary)
        ranked = sorted(
            sentences,
            key=lambda sentence: (
                self._score_setting_sentence(sentence),
                -sentences.index(sentence),
            ),
            reverse=True,
        )
        if ranked and self._score_setting_sentence(ranked[0]) > 0:
            return ranked[0]
        for sentence in sentences:
            if any(token in sentence for token in _PERSONA_TOKENS):
                return sentence
        return sentences[0] if sentences else "一个世界正在等待主角推门而入。"

    def _score_setting_sentence(self, sentence: str) -> int:
        setting_score = sum(2 for token in _SETTING_TOKENS if token in sentence)
        persona_penalty = sum(3 for token in _PERSONA_TOKENS if token in sentence)
        return setting_score - persona_penalty

    def _extract_title_candidate(self, sentence: str) -> str:
        if not sentence:
            return ""

        clause = re.split(r"[，。！？!?：:；;]", sentence, maxsplit=1)[0]
        normalized = clause
        normalized = re.sub(r"^(?:这是一座被|这是一座|这是一片被|这是一片|这是一处被|这是一处|这是一个|一座被|一座|一片|一处|一个)", "", normalized)
        normalized = normalized.replace("海港城市", "海港城").replace("港口城市", "港城")

        if "海港" in normalized and "高墙" in sentence:
            return "高墙海港城"

        place_match = re.search(
            r"([\u4e00-\u9fff]{0,8}(?:海港城|港城|小镇|都市|城市|城邦|王朝|学院|群岛|帝国|荒原|大陆|要塞|世界|海港|镇))",
            normalized,
        )
        if place_match:
            candidate = place_match.group(1)
            candidate = re.sub(r"^(?:被|近未来|未来|潮湿|霓虹|雾中|雾里)+", "", candidate)
            candidate = candidate.replace("城市", "城")
            if candidate.endswith("海港") and ("城" in normalized or "城市" in clause):
                candidate = f"{candidate}城"
            return candidate.strip("，。！？!?：:；; ")

        cleaned = re.sub(r"[，。！？、：；,.!?\s]+", "", normalized)
        return cleaned[:8]

    def _extract_core_tension(self, summary: str, *, protagonist_hook: str = "") -> str:
        for sentence in self._split_sentences(summary):
            if sentence != protagonist_hook and any(token in sentence for token in ("张力", "冲突", "对抗", "秩序", "资源", "攀爬", "代价", "压")):
                return sentence
        sentences = self._split_sentences(summary)
        if len(sentences) > 1:
            for sentence in sentences[1:]:
                if sentence != protagonist_hook:
                    return sentence
        return sentences[0] if sentences else "世界的核心张力仍在等待被命名。"

    def _derive_title(self, world_summary: str, protagonist_hook: str, core_tension: str) -> str:
        candidate = self._extract_title_candidate(protagonist_hook or world_summary)
        if candidate:
            return candidate

        base = world_summary or protagonist_hook or core_tension
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
        if "慢" in player_profile or "克制" in player_profile:
            fallback.append("克制")
        if "城" in world_summary or "都市" in world_summary:
            fallback.append("都市")
        if "成长" in world_summary or "向上" in world_summary:
            fallback.append("成长")
        return fallback[:5] or ["写实", "克制"]
