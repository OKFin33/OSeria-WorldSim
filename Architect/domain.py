"""Canonical vNext domain models for the Architect pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


def _unique_strings(values: list[str] | tuple[str, ...] | None) -> list[str]:
    if not values:
        return []
    seen: list[str] = []
    for raw in values:
        text = str(raw).strip()
        if text and text not in seen:
            seen.append(text)
    return seen


@dataclass
class RoutingSnapshot:
    confirmed: list[str] = field(default_factory=list)
    exploring: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)
    untouched: list[str] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "RoutingSnapshot":
        return cls()

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "RoutingSnapshot":
        payload = payload or {}
        return cls(
            confirmed=_unique_strings(payload.get("confirmed")),
            exploring=_unique_strings(payload.get("exploring")),
            excluded=_unique_strings(payload.get("excluded")),
            untouched=_unique_strings(payload.get("untouched")),
        )

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "confirmed": _unique_strings(self.confirmed),
            "exploring": _unique_strings(self.exploring),
            "excluded": _unique_strings(self.excluded),
            "untouched": _unique_strings(self.untouched),
        }


@dataclass
class WorldSoftSignals:
    notable_imagery: list[str] = field(default_factory=list)
    unstable_hypotheses: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "WorldSoftSignals":
        payload = payload or {}
        return cls(
            notable_imagery=_unique_strings(payload.get("notable_imagery")),
            unstable_hypotheses=_unique_strings(payload.get("unstable_hypotheses")),
        )

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "notable_imagery": _unique_strings(self.notable_imagery),
            "unstable_hypotheses": _unique_strings(self.unstable_hypotheses),
        }


@dataclass
class PlayerSoftSignals:
    notable_phrasing: list[str] = field(default_factory=list)
    subtext_hypotheses: list[str] = field(default_factory=list)
    style_notes: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "PlayerSoftSignals":
        payload = payload or {}
        return cls(
            notable_phrasing=_unique_strings(payload.get("notable_phrasing")),
            subtext_hypotheses=_unique_strings(payload.get("subtext_hypotheses")),
            style_notes=str(payload.get("style_notes", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "notable_phrasing": _unique_strings(self.notable_phrasing),
            "subtext_hypotheses": _unique_strings(self.subtext_hypotheses),
            "style_notes": self.style_notes.strip(),
        }


@dataclass
class WorldDossier:
    world_premise: str = ""
    tension_guess: str = ""
    scene_anchor: str = ""
    open_threads: list[str] = field(default_factory=list)
    soft_signals: WorldSoftSignals = field(default_factory=WorldSoftSignals)

    @classmethod
    def empty(cls) -> "WorldDossier":
        return cls()

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "WorldDossier":
        payload = payload or {}
        return cls(
            world_premise=str(payload.get("world_premise", "")).strip(),
            tension_guess=str(payload.get("tension_guess", "")).strip(),
            scene_anchor=str(payload.get("scene_anchor", "")).strip(),
            open_threads=_unique_strings(payload.get("open_threads")),
            soft_signals=WorldSoftSignals.from_dict(payload.get("soft_signals")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_premise": self.world_premise.strip(),
            "tension_guess": self.tension_guess.strip(),
            "scene_anchor": self.scene_anchor.strip(),
            "open_threads": _unique_strings(self.open_threads),
            "soft_signals": self.soft_signals.to_dict(),
        }


@dataclass
class PlayerDossier:
    fantasy_vector: str = ""
    emotional_seed: str = ""
    taste_bias: str = ""
    language_register: str = ""
    user_no_go_zones: list[str] = field(default_factory=list)
    soft_signals: PlayerSoftSignals = field(default_factory=PlayerSoftSignals)

    @classmethod
    def empty(cls) -> "PlayerDossier":
        return cls()

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "PlayerDossier":
        payload = payload or {}
        return cls(
            fantasy_vector=str(payload.get("fantasy_vector", "")).strip(),
            emotional_seed=str(payload.get("emotional_seed", "")).strip(),
            taste_bias=str(payload.get("taste_bias", "")).strip(),
            language_register=str(payload.get("language_register", "")).strip(),
            user_no_go_zones=_unique_strings(payload.get("user_no_go_zones")),
            soft_signals=PlayerSoftSignals.from_dict(payload.get("soft_signals")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "fantasy_vector": self.fantasy_vector.strip(),
            "emotional_seed": self.emotional_seed.strip(),
            "taste_bias": self.taste_bias.strip(),
            "language_register": self.language_register.strip(),
            "user_no_go_zones": _unique_strings(self.user_no_go_zones),
            "soft_signals": self.soft_signals.to_dict(),
        }


@dataclass
class ChangeLog:
    newly_confirmed: list[str] = field(default_factory=list)
    newly_rejected: list[str] = field(default_factory=list)
    needs_follow_up: list[str] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "ChangeLog":
        return cls()

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ChangeLog":
        payload = payload or {}
        return cls(
            newly_confirmed=_unique_strings(payload.get("newly_confirmed")),
            newly_rejected=_unique_strings(payload.get("newly_rejected")),
            needs_follow_up=_unique_strings(payload.get("needs_follow_up")),
        )

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "newly_confirmed": _unique_strings(self.newly_confirmed),
            "newly_rejected": _unique_strings(self.newly_rejected),
            "needs_follow_up": _unique_strings(self.needs_follow_up),
        }


@dataclass
class TwinDossier:
    routing_snapshot: RoutingSnapshot = field(default_factory=RoutingSnapshot.empty)
    world_dossier: WorldDossier = field(default_factory=WorldDossier.empty)
    player_dossier: PlayerDossier = field(default_factory=PlayerDossier.empty)
    change_log: ChangeLog = field(default_factory=ChangeLog.empty)

    @classmethod
    def empty(cls) -> "TwinDossier":
        return cls()

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "TwinDossier":
        payload = payload or {}
        return cls(
            routing_snapshot=RoutingSnapshot.from_dict(payload.get("routing_snapshot")),
            world_dossier=WorldDossier.from_dict(payload.get("world_dossier")),
            player_dossier=PlayerDossier.from_dict(payload.get("player_dossier")),
            change_log=ChangeLog.from_dict(payload.get("change_log")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "routing_snapshot": self.routing_snapshot.to_dict(),
            "world_dossier": self.world_dossier.to_dict(),
            "player_dossier": self.player_dossier.to_dict(),
            "change_log": self.change_log.to_dict(),
        }


DossierUpdateStatus = Literal["updated", "conservative_update", "update_skipped", "hard_failed"]
FollowUpSignal = Literal["", "mirror_rejected"]
BubbleKind = Literal["answer", "advance"]
TurnTransactionStatus = Literal["idle", "pending_turn", "pending_response_generation", "pending_compile"]


@dataclass
class BubbleCandidate:
    text: str
    kind: BubbleKind

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BubbleCandidate":
        kind = str(payload.get("kind", "answer")).strip()
        if kind not in {"answer", "advance"}:
            kind = "answer"
        return cls(text=str(payload.get("text", "")).strip(), kind=kind)  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, str]:
        return {"text": self.text.strip(), "kind": self.kind}


@dataclass
class CompileOutput:
    confirmed_dimensions: list[str] = field(default_factory=list)
    emergent_dimensions: list[str] = field(default_factory=list)
    excluded_dimensions: list[str] = field(default_factory=list)
    narrative_briefing: str = ""
    player_profile: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "CompileOutput":
        payload = payload or {}
        return cls(
            confirmed_dimensions=_unique_strings(payload.get("confirmed_dimensions")),
            emergent_dimensions=_unique_strings(payload.get("emergent_dimensions")),
            excluded_dimensions=_unique_strings(payload.get("excluded_dimensions")),
            narrative_briefing=str(payload.get("narrative_briefing", "")).strip(),
            player_profile=str(payload.get("player_profile", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "confirmed_dimensions": _unique_strings(self.confirmed_dimensions),
            "emergent_dimensions": _unique_strings(self.emergent_dimensions),
            "excluded_dimensions": _unique_strings(self.excluded_dimensions),
            "narrative_briefing": self.narrative_briefing.strip(),
            "player_profile": self.player_profile.strip(),
        }


@dataclass
class ForgeContext:
    world_premise: str = ""
    tension_guess: str = ""
    scene_anchor: str = ""
    fantasy_vector: str = ""
    emotional_seed: str = ""
    taste_bias: str = ""
    language_register: str = ""
    user_no_go_zones: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AssemblerContext:
    world_premise: str = ""
    tension_guess: str = ""
    scene_anchor: str = ""
    notable_imagery: list[str] = field(default_factory=list)
    fantasy_vector: str = ""
    emotional_seed: str = ""
    taste_bias: str = ""
    language_register: str = ""
    user_no_go_zones: list[str] = field(default_factory=list)
    notable_phrasing: list[str] = field(default_factory=list)
    style_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FrozenCompilePackage:
    compile_output: CompileOutput
    forge_context: ForgeContext
    assembler_context: AssemblerContext


def build_forge_context(dossier: TwinDossier) -> ForgeContext:
    return ForgeContext(
        world_premise=dossier.world_dossier.world_premise,
        tension_guess=dossier.world_dossier.tension_guess,
        scene_anchor=dossier.world_dossier.scene_anchor,
        fantasy_vector=dossier.player_dossier.fantasy_vector,
        emotional_seed=dossier.player_dossier.emotional_seed,
        taste_bias=dossier.player_dossier.taste_bias,
        language_register=dossier.player_dossier.language_register,
        user_no_go_zones=_unique_strings(dossier.player_dossier.user_no_go_zones),
    )


def build_assembler_context(dossier: TwinDossier) -> AssemblerContext:
    return AssemblerContext(
        world_premise=dossier.world_dossier.world_premise,
        tension_guess=dossier.world_dossier.tension_guess,
        scene_anchor=dossier.world_dossier.scene_anchor,
        notable_imagery=_unique_strings(dossier.world_dossier.soft_signals.notable_imagery),
        fantasy_vector=dossier.player_dossier.fantasy_vector,
        emotional_seed=dossier.player_dossier.emotional_seed,
        taste_bias=dossier.player_dossier.taste_bias,
        language_register=dossier.player_dossier.language_register,
        user_no_go_zones=_unique_strings(dossier.player_dossier.user_no_go_zones),
        notable_phrasing=_unique_strings(dossier.player_dossier.soft_signals.notable_phrasing),
        style_notes=dossier.player_dossier.soft_signals.style_notes,
    )
