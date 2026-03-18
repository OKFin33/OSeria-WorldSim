"""Lorebook routing, merge, and retrieval helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Iterable

from .domain import LorebookCandidate, LorebookEntry, StageRecord


def normalize_name(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.lower())


def stage_id_from_label(label: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", "-", label.strip().lower())
    return cleaned.strip("-") or "default-stage"


@dataclass
class LorebookMergeResult:
    entries: list[LorebookEntry]
    stages: list[StageRecord]
    changed_entries: list[LorebookEntry]
    conflicts: list[dict[str, object]]
    stats: dict[str, int]


@dataclass
class StageSelection:
    primary_stage_id: str
    supporting_stage_ids: list[str]
    source: str = ""


def route_stages(
    *,
    user_action: str,
    recent_messages: list[str],
    current_location: str,
    current_situation: str,
    active_threads: list[str],
    stages: list[StageRecord],
    current_active_stage_id: str = "",
) -> StageSelection:
    if not stages:
        return _provisional_stage_selection(
            user_action=user_action,
            recent_messages=recent_messages,
            current_location=current_location,
            current_situation=current_situation,
            active_threads=active_threads,
            current_active_stage_id=current_active_stage_id,
        )

    context_parts = [
        user_action,
        current_location,
        current_situation,
        *active_threads,
        *recent_messages,
    ]
    context = "\n".join(part.strip().lower() for part in context_parts if part.strip())
    if not context:
        if current_active_stage_id and any(stage.id == current_active_stage_id for stage in stages):
            return StageSelection(
                primary_stage_id=current_active_stage_id,
                supporting_stage_ids=[],
                source="lorebook",
            )
        return _provisional_stage_selection(
            user_action=user_action,
            recent_messages=recent_messages,
            current_location=current_location,
            current_situation=current_situation,
            active_threads=active_threads,
            current_active_stage_id=current_active_stage_id,
        )

    scored: list[tuple[int, StageRecord]] = []
    for stage in stages:
        score = 0
        candidates = [stage.label, *stage.aliases]
        for candidate in candidates:
            text = candidate.lower().strip()
            if not text:
                continue
            if text in context:
                score += 4
            elif any(token and token in context for token in text.split()):
                score += 1
        if stage.id == current_active_stage_id and score >= 0:
            score += 2
        if score > 0:
            scored.append((score, stage))

    scored.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
    if not scored:
        if current_active_stage_id and any(stage.id == current_active_stage_id for stage in stages):
            return StageSelection(
                primary_stage_id=current_active_stage_id,
                supporting_stage_ids=[],
                source="lorebook",
            )
        return _provisional_stage_selection(
            user_action=user_action,
            recent_messages=recent_messages,
            current_location=current_location,
            current_situation=current_situation,
            active_threads=active_threads,
            current_active_stage_id=current_active_stage_id,
        )

    primary = scored[0][1].id
    supporting = [stage.id for _, stage in scored[1:3] if stage.id != primary]
    return StageSelection(primary_stage_id=primary, supporting_stage_ids=supporting, source="lorebook")


def select_relevant_entries(
    *,
    query: str,
    recent_messages: list[str],
    entries: list[LorebookEntry],
    primary_stage_id: str,
    supporting_stage_ids: list[str],
    l1_limit: int = 4,
    l2_limit: int = 2,
) -> list[LorebookEntry]:
    context = "\n".join([query, *recent_messages]).lower().strip()
    if not context:
        return []

    allowed_stage_ids = {stage_id for stage_id in [primary_stage_id, *supporting_stage_ids] if stage_id}
    stage_scoped_entries = [
        entry for entry in entries if not allowed_stage_ids or not entry.stage_id or entry.stage_id in allowed_stage_ids
    ]

    scored_l1: list[tuple[int, LorebookEntry]] = []
    for entry in stage_scoped_entries:
        if entry.layer != 1:
            continue
        score = _score_entry(entry, context, primary_stage_id=primary_stage_id, supporting_stage_ids=supporting_stage_ids)
        if score > 0:
            scored_l1.append((score, entry))
    scored_l1.sort(key=lambda item: (item[0], item[1].last_updated_turn), reverse=True)
    selected_l1 = [entry for _, entry in scored_l1[:l1_limit]]

    selected_l1_ids = {entry.id for entry in selected_l1}
    scored_l2: list[tuple[int, LorebookEntry]] = []
    for entry in stage_scoped_entries:
        if entry.layer != 2 or not entry.parent_id or entry.parent_id not in selected_l1_ids:
            continue
        score = _score_entry(entry, context, primary_stage_id=primary_stage_id, supporting_stage_ids=supporting_stage_ids)
        if score > 0:
            scored_l2.append((score, entry))
    scored_l2.sort(key=lambda item: (item[0], item[1].last_updated_turn), reverse=True)
    selected_l2 = [entry for _, entry in scored_l2[:l2_limit]]

    return [*selected_l1, *selected_l2]


def parse_candidates(
    extracted: Iterable[dict[str, object]],
    *,
    default_stage_label: str,
) -> list[LorebookCandidate]:
    candidates: list[LorebookCandidate] = []
    for raw in extracted:
        candidate = LorebookCandidate.from_dict(raw, default_stage_label=default_stage_label)
        if candidate is None:
            continue
        candidates.append(candidate)
    return candidates


def merge_candidates(
    *,
    existing_entries: list[LorebookEntry],
    existing_stages: list[StageRecord],
    candidates: Iterable[LorebookCandidate],
    turn_number: int,
) -> LorebookMergeResult:
    updated_entries = list(existing_entries)
    updated_stages = [StageRecord.from_dict(stage.to_dict()) for stage in existing_stages]
    changed_entries: list[LorebookEntry] = []
    conflicts: list[dict[str, object]] = []
    inserted = 0
    updated = 0

    stage_by_id = {stage.id: stage for stage in updated_stages}
    stage_name_index = {
        normalize_name(candidate): stage.id
        for stage in updated_stages
        for candidate in [stage.label, *stage.aliases]
        if candidate.strip()
    }

    pending_l2: list[tuple[LorebookCandidate, str]] = []
    orphan_l2 = 0
    dropped = 0
    downgraded_l2 = 0

    for candidate in candidates:
        stage_id = _ensure_stage(candidate.stage_label, candidate.description, updated_stages, stage_by_id, stage_name_index)
        if candidate.layer == 2:
            pending_l2.append((candidate, stage_id))
            continue
        result = _merge_candidate(
            updated_entries=updated_entries,
            candidate=candidate,
            stage_id=stage_id,
            parent_id="",
            turn_number=turn_number,
        )
        if result["kind"] == "insert":
            inserted += 1
            changed_entries.append(result["entry"])
        elif result["kind"] == "update":
            updated += 1
            changed_entries.append(result["entry"])
        else:
            conflicts.append(result["conflict"])

    for candidate, stage_id in pending_l2:
        parent_id = _resolve_parent_id(candidate.parent_hint, updated_entries, stage_id)
        if not parent_id:
            if candidate.type == "event":
                orphan_l2 += 1
                dropped += 1
                conflicts.append(
                    {
                        "candidate_name": candidate.name,
                        "candidate_type": candidate.type,
                        "candidate_stage_id": stage_id,
                        "reason": "orphan_l2",
                        "matched_entry_ids": [],
                    }
                )
                continue
            candidate = replace(candidate, layer=1, parent_hint="")
            downgraded_l2 += 1
        result = _merge_candidate(
            updated_entries=updated_entries,
            candidate=candidate,
            stage_id=stage_id,
            parent_id=parent_id,
            turn_number=turn_number,
        )
        if result["kind"] == "insert":
            inserted += 1
            changed_entries.append(result["entry"])
        elif result["kind"] == "update":
            updated += 1
            changed_entries.append(result["entry"])
        else:
            conflicts.append(result["conflict"])

    stats = {
        "inserted": inserted,
        "updated": updated,
        "conflicts": len(conflicts),
        "total": len(updated_entries),
        "orphan_l2": orphan_l2,
        "dropped": dropped,
        "downgraded_l2": downgraded_l2,
    }
    return LorebookMergeResult(
        entries=updated_entries,
        stages=updated_stages,
        changed_entries=changed_entries,
        conflicts=conflicts,
        stats=stats,
    )


def _ensure_stage(
    label: str,
    description: str,
    updated_stages: list[StageRecord],
    stage_by_id: dict[str, StageRecord],
    stage_name_index: dict[str, str],
) -> str:
    normalized_label = normalize_name(label)
    existing_stage_id = stage_name_index.get(normalized_label)
    if existing_stage_id:
        stage = stage_by_id[existing_stage_id]
        if description and not stage.description:
            stage.description = description.strip()
        stage.touch()
        return stage.id

    stage_id = stage_id_from_label(label)
    suffix = 2
    while stage_id in stage_by_id:
        stage_id = f"{stage_id}-{suffix}"
        suffix += 1
    stage = StageRecord.create(stage_id=stage_id, label=label, description=description)
    updated_stages.append(stage)
    stage_by_id[stage.id] = stage
    for candidate in [stage.label, *stage.aliases]:
        key = normalize_name(candidate)
        if key:
            stage_name_index[key] = stage.id
    return stage.id


def _merge_candidate(
    *,
    updated_entries: list[LorebookEntry],
    candidate: LorebookCandidate,
    stage_id: str,
    parent_id: str,
    turn_number: int,
) -> dict[str, object]:
    if candidate.layer == 2 and not parent_id:
        return {
            "kind": "conflict",
            "conflict": _build_conflict(candidate, stage_id, "orphan_l2", []),
        }
    matches = _find_existing_matches(updated_entries, candidate, stage_id)
    if len(matches) > 1:
        return {
            "kind": "conflict",
            "conflict": _build_conflict(candidate, stage_id, "multiple_matches", [updated_entries[index] for index in matches]),
        }
    if len(matches) == 1:
        current = updated_entries[matches[0]]
        if current.type != candidate.type:
            return {
                "kind": "conflict",
                "conflict": _build_conflict(candidate, stage_id, "type_conflict", [current]),
            }
        if current.stage_id and stage_id and current.stage_id != stage_id:
            return {
                "kind": "conflict",
                "conflict": _build_conflict(candidate, stage_id, "stage_conflict", [current]),
            }
        if _descriptions_conflict(current.description, candidate.description):
            return {
                "kind": "conflict",
                "conflict": _build_conflict(candidate, stage_id, "description_conflict", [current]),
            }
        current.aliases = _merge_strings(current.aliases, candidate.aliases)
        current.keywords = _merge_strings(current.keywords, candidate.keywords)
        current.activation_keys = _merge_strings(
            current.activation_keys,
            [current.name, *current.aliases, *current.keywords, *candidate.keywords, *candidate.aliases],
        )
        if candidate.description:
            current.description = candidate.description
        if candidate.status:
            current.status = candidate.status
        current.stage_id = current.stage_id or stage_id
        current.layer = candidate.layer
        if candidate.layer == 2 and parent_id:
            current.parent_id = parent_id
        current.last_updated_turn = turn_number
        current.source_turns = list(dict.fromkeys([*current.source_turns, *candidate.source_turns, turn_number]))
        current.evidence_snippets = _merge_strings(current.evidence_snippets, candidate.evidence_snippets)
        return {"kind": "update", "entry": current}

    entry = LorebookEntry.create(
        entry_type=candidate.type,
        name=candidate.name,
        aliases=candidate.aliases,
        keywords=candidate.keywords,
        description=candidate.description,
        turn_number=turn_number,
        status=candidate.status,
        stage_id=stage_id,
        layer=candidate.layer,
        parent_id=parent_id if candidate.layer == 2 else "",
        activation_keys=[candidate.name, *candidate.aliases, *candidate.keywords],
        evidence_snippets=candidate.evidence_snippets,
    )
    if candidate.source_turns:
        entry.source_turns = list(dict.fromkeys([*entry.source_turns, *candidate.source_turns]))
    updated_entries.append(entry)
    return {"kind": "insert", "entry": entry}


def _find_existing_matches(entries: list[LorebookEntry], candidate: LorebookCandidate, stage_id: str) -> list[int]:
    candidate_keys = {normalize_name(candidate.name), *(normalize_name(item) for item in candidate.aliases)}
    candidate_keys.discard("")
    matches: list[int] = []
    for index, entry in enumerate(entries):
        known_names = {
            normalize_name(entry.name),
            *(normalize_name(item) for item in entry.aliases),
        }
        if not candidate_keys & known_names:
            continue
        if entry.stage_id and stage_id and entry.stage_id not in {"", stage_id}:
            continue
        matches.append(index)
    return matches


def _resolve_parent_id(parent_hint: str, entries: list[LorebookEntry], stage_id: str) -> str:
    normalized_hint = normalize_name(parent_hint)
    if not normalized_hint:
        return ""
    for entry in entries:
        if entry.layer != 1:
            continue
        if stage_id and entry.stage_id and entry.stage_id != stage_id:
            continue
        known_names = {normalize_name(entry.name), *(normalize_name(item) for item in entry.aliases)}
        if normalized_hint in known_names:
            return entry.id
    return ""


def _build_conflict(
    candidate: LorebookCandidate,
    stage_id: str,
    reason: str,
    matched_entries: list[LorebookEntry],
) -> dict[str, object]:
    return {
        "candidate_name": candidate.name,
        "candidate_type": candidate.type,
        "candidate_stage_id": stage_id,
        "reason": reason,
        "matched_entry_ids": [entry.id for entry in matched_entries],
    }


def _descriptions_conflict(existing: str, incoming: str) -> bool:
    left = normalize_name(existing)
    right = normalize_name(incoming)
    if not left or not right or left == right:
        return False
    if left in right or right in left:
        return False
    return len(left) > 12 and len(right) > 12


def _score_entry(
    entry: LorebookEntry,
    context: str,
    *,
    primary_stage_id: str,
    supporting_stage_ids: list[str],
) -> int:
    score = 0
    for candidate in entry.activation_keys or [entry.name, *entry.aliases, *entry.keywords]:
        text = candidate.lower().strip()
        if not text:
            continue
        if text in context:
            score += 3
        elif any(token and token in context for token in text.split()):
            score += 1
    if entry.stage_id and entry.stage_id == primary_stage_id:
        score += 3
    elif entry.stage_id and entry.stage_id in supporting_stage_ids:
        score += 1
    return score


def _merge_strings(base: list[str], new_items: list[str]) -> list[str]:
    merged = [item for item in base if item.strip()]
    for item in new_items:
        if item and item not in merged:
            merged.append(item)
    return merged


def _provisional_stage_selection(
    *,
    user_action: str,
    recent_messages: list[str],
    current_location: str,
    current_situation: str,
    active_threads: list[str],
    current_active_stage_id: str,
) -> StageSelection:
    labels = [
        current_location.strip(),
        *(item.strip() for item in active_threads if item.strip()),
        current_situation.strip(),
        *(item.strip() for item in recent_messages[-2:] if item.strip()),
        user_action.strip(),
    ]
    seen: list[str] = []
    for raw in labels:
        cleaned = raw.strip()
        if not cleaned:
            continue
        snippet = cleaned[:48]
        if snippet not in seen:
            seen.append(snippet)
    if seen:
        primary = f"provisional-{stage_id_from_label(seen[0])}"
        supporting = [f"provisional-{stage_id_from_label(label)}" for label in seen[1:3]]
        return StageSelection(primary_stage_id=primary, supporting_stage_ids=supporting, source="provisional")
    if current_active_stage_id:
        return StageSelection(
            primary_stage_id=current_active_stage_id,
            supporting_stage_ids=[],
            source="provisional",
        )
    return StageSelection(
        primary_stage_id="provisional-default-stage",
        supporting_stage_ids=[],
        source="provisional",
    )
