"""Deterministic generation of user-facing interview bubbles."""

from __future__ import annotations

import re

from .dimension_registry import InterviewDimensionRegistry

MAX_SUGGESTED_TAGS = 3
MIN_SUGGESTED_TAGS = 2
MAX_BUBBLE_LENGTH = 18
CJK_RE = re.compile(r"[\u3400-\u9fff]")
QUOTE_RE = re.compile(r"[「“\"『](.+?)[」”\"』]")


class BubbleSuggester:
    def __init__(self, registry: InterviewDimensionRegistry) -> None:
        self.registry = registry

    def build(
        self,
        *,
        question: str,
        turn: int,
        routing_snapshot: dict[str, list[str]],
    ) -> list[str]:
        suggestions: list[str] = []

        for bubble in self._question_semantic_bubbles(question):
            self._push(suggestions, bubble)

        for bubble in self._anchor_bubbles(question):
            self._push(suggestions, bubble)

        if len(suggestions) < MAX_SUGGESTED_TAGS:
            dimension_order = self._rank_dimensions(routing_snapshot)
            seed_text = f"{turn}:{question}"
            for dimension_id in dimension_order:
                for bubble in self.registry.bubble_prompts_for_dimension(dimension_id, seed_text=seed_text):
                    if self._push(suggestions, bubble):
                        break
                if len(suggestions) >= MAX_SUGGESTED_TAGS:
                    break

        if len(suggestions) < MIN_SUGGESTED_TAGS:
            fragment = self._question_fragment(question)
            self._push(suggestions, fragment)

        return suggestions[:MAX_SUGGESTED_TAGS]

    def _question_semantic_bubbles(self, question: str) -> list[str]:
        semantic: list[str] = []
        for option in self._contrast_option_bubbles(question):
            if option not in semantic:
                semantic.append(option)
        focus = self._focus_bubble(question)
        if focus and focus not in semantic:
            semantic.append(focus)
        return semantic

    def _rank_dimensions(self, routing_snapshot: dict[str, list[str]]) -> list[str]:
        ordered = [
            *self.registry.sort_dimensions(routing_snapshot.get("exploring", []), strategy="natural"),
            *self.registry.sort_dimensions(routing_snapshot.get("untouched", []), strategy="natural"),
            *self.registry.sort_dimensions(routing_snapshot.get("confirmed", []), strategy="natural"),
        ]
        unique: list[str] = []
        for dimension_id in ordered:
            if dimension_id not in unique:
                unique.append(dimension_id)
        return unique

    def _anchor_bubbles(self, question: str) -> list[str]:
        anchors = [self._clean(text) for text in QUOTE_RE.findall(question)]
        anchors = [anchor for anchor in anchors if self._is_displayable(anchor)]
        unique_anchors: list[str] = []
        for anchor in anchors:
            if anchor not in unique_anchors:
                unique_anchors.append(anchor)

        suggestions: list[str] = []
        for anchor in unique_anchors[:2]:
            bubble = self._anchor_prompt(anchor, question)
            if bubble:
                suggestions.append(bubble)

        if len(unique_anchors) >= 2 and "还是" in question:
            suggestions.append("你更想靠近哪一边")
        return suggestions

    def _contrast_option_bubbles(self, question: str) -> list[str]:
        if "还是" not in question:
            return []

        first_sentence = re.split(r"[？?]", question, maxsplit=1)[0]
        if "还是" not in first_sentence:
            return []

        left_raw, right_raw = first_sentence.split("还是", 1)
        left = self._normalize_option(left_raw, side="left")
        right = self._normalize_option(right_raw, side="right")
        bubbles: list[str] = []
        for option in (left, right):
            if self._is_displayable(option):
                bubbles.append(option)
        return bubbles[:2]

    def _normalize_option(self, text: str, *, side: str) -> str:
        cleaned = self._clean(text)
        markers = [
            "更想看到的是",
            "想看到的是",
            "看到的是",
            "看见的是",
            "更想要的是",
            "想要的是",
            "更喜欢的是",
            "喜欢的是",
            "是",
        ]
        for marker in markers:
            if marker in cleaned:
                cleaned = cleaned.rsplit(marker, 1)[-1].strip()
                break

        if side == "right":
            cleaned = re.sub(r"^(更|更像|更偏向|偏向|像)\s*", "", cleaned)
            cleaned = re.sub(r"^更?日常的[、，]?", "", cleaned)

        cleaned = cleaned.strip("，,、 ")
        cleaned = re.sub(r"^(那个|一种|一个)", "", cleaned).strip()
        return cleaned

    def _focus_bubble(self, question: str) -> str | None:
        match = re.search(r"(最让你[^，。？?]{2,18}?(?:细节|画面|瞬间|地方|部分))", question)
        if match:
            bubble = match.group(1).replace("那个", "")
            return bubble.strip()
        if "什么" in question:
            fragment = self._question_fragment(question)
            if fragment != "再往前想一步":
                return fragment
        return None

    def _anchor_prompt(self, anchor: str, question: str) -> str | None:
        wrapped = f"「{anchor}」"
        if any(token in anchor for token in ("台", "广播", "播", "喇叭", "论坛")):
            return f"{wrapped}在传什么"
        if any(token in anchor for token in ("部", "局", "司", "会", "团", "组", "廷", "府")):
            return f"{wrapped}在护着谁"
        if any(token in question for token in ("秩序", "表象", "维持")):
            return f"{wrapped}在掩盖什么"
        return f"{wrapped}背后是谁"

    def _question_fragment(self, question: str) -> str:
        text = re.sub(r"[？?。！!]+", "", question).strip()
        text = re.sub(r"^(那么|所以|此刻|在这里|现在|如果)\s*", "", text)
        text = re.sub(r"^你(?:更)?想(?:知道|看到|先看)?", "", text)
        text = text.strip("，,、 ")
        if 4 <= len(text) <= MAX_BUBBLE_LENGTH and CJK_RE.search(text):
            return text
        return "再往前想一步"

    def _push(self, suggestions: list[str], bubble: str | None) -> bool:
        if bubble is None:
            return False
        cleaned = self._clean(bubble)
        if not self._is_displayable(cleaned):
            return False
        if cleaned in suggestions:
            return False
        suggestions.append(cleaned)
        return True

    def _is_displayable(self, bubble: str) -> bool:
        if len(bubble) < 4 or len(bubble) > MAX_BUBBLE_LENGTH:
            return False
        if not CJK_RE.search(bubble):
            return False
        return True

    @staticmethod
    def _clean(text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned.strip("`\"'[](){}<>:：;；,.，。!?！？")
