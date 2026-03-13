"""Lorebook selection and upsert helpers."""

from __future__ import annotations

import re
from typing import Iterable

from .domain import LorebookEntry, LorebookType


def normalize_name(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.lower())


def select_relevant_entries(
    query: str,
    entries: list[LorebookEntry],
    *,
    limit: int = 5,
) -> list[LorebookEntry]:
    normalized_query = query.lower()
    if not normalized_query.strip():
        return []

    scored: list[tuple[int, LorebookEntry]] = []
    for entry in entries:
        score = 0
        candidates = [entry.name, *entry.aliases, *entry.keywords]
        for candidate in candidates:
            text = candidate.lower().strip()
            if not text:
                continue
            if text in normalized_query:
                score += 3
            elif any(token and token in normalized_query for token in text.split()):
                score += 1
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda item: (item[0], item[1].last_updated_turn), reverse=True)
    return [entry for _, entry in scored[:limit]]


def upsert_entries(
    existing: list[LorebookEntry],
    extracted: Iterable[dict[str, object]],
    *,
    turn_number: int,
) -> tuple[list[LorebookEntry], list[LorebookEntry], dict[str, int]]:
    updated_entries = list(existing)
    inserted = 0
    updated = 0
    changed: list[LorebookEntry] = []

    for raw in extracted:
        entry_type = str(raw.get("type", "concept")).strip()
        if entry_type not in {"character", "location", "event", "concept", "faction"}:
            entry_type = "concept"
        name = str(raw.get("name", "")).strip()
        if not name:
            continue
        aliases = [str(item).strip() for item in raw.get("aliases", []) if str(item).strip()]
        keywords = [str(item).strip() for item in raw.get("keywords", []) if str(item).strip()]
        description = str(raw.get("description", "")).strip()
        status = str(raw.get("status", "")).strip()
        match_index = _find_existing_index(updated_entries, name, aliases)

        if match_index is None:
            entry = LorebookEntry.create(
                entry_type=entry_type,  # type: ignore[arg-type]
                name=name,
                aliases=aliases,
                keywords=keywords,
                description=description,
                turn_number=turn_number,
                status=status,
            )
            updated_entries.append(entry)
            changed.append(entry)
            inserted += 1
            continue

        current = updated_entries[match_index]
        current.aliases = _merge_strings(current.aliases, aliases)
        current.keywords = _merge_strings(current.keywords, keywords)
        if description:
            current.description = description
        if status:
            current.status = status
        current.last_updated_turn = turn_number
        current.source_turns = list(dict.fromkeys([*current.source_turns, turn_number]))
        changed.append(current)
        updated += 1

    stats = {"inserted": inserted, "updated": updated, "total": len(updated_entries)}
    return updated_entries, changed, stats


def _find_existing_index(entries: list[LorebookEntry], name: str, aliases: list[str]) -> int | None:
    normalized_candidates = {normalize_name(name), *(normalize_name(item) for item in aliases)}
    normalized_candidates.discard("")
    for index, entry in enumerate(entries):
        known_names = {normalize_name(entry.name), *(normalize_name(item) for item in entry.aliases)}
        if normalized_candidates & known_names:
            return index
    return None


def _merge_strings(base: list[str], new_items: list[str]) -> list[str]:
    merged = [item for item in base if item.strip()]
    for item in new_items:
        if item and item not in merged:
            merged.append(item)
    return merged
