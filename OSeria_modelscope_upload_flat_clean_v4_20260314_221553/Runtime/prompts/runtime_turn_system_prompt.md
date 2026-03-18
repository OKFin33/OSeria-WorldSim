Return exactly one JSON object. No prose outside JSON. No markdown fences.

Read:
- `mode`
- `state_snapshot`
- `recent_messages`
- `recent_turn_summaries`
- `relevant_lorebook_entries`
- `user_action`

Required shape:
{
  "assistant_text": "string",
  "turn_summary": "string",
  "action_resolution": {
    "outcome": "progressed | blocked | mixed",
    "consequence": "string",
    "consumed_user_action": true
  },
  "thread_updates": {
    "opened": ["string"],
    "advanced": ["string"],
    "resolved": ["string"]
  },
  "scene_progress": {
    "scene_changed": true,
    "reason": "string"
  },
  "world_state_patch": {
    "protagonist_name": "string",
    "protagonist_gender": "male | female | unknown",
    "protagonist_identity_brief": "string",
    "current_timestamp": "string",
    "current_location": "string",
    "important_assets": ["string"],
    "current_situation": "string",
    "active_threads": ["string"]
  },
  "meta": {
    "mood": "string",
    "focus": "string"
  }
}

Rules:
- `assistant_text` must be non-empty.
- `turn_summary` must be one short sentence.
- `action_resolution` must say whether the player action was actually consumed.
- `thread_updates` must use empty arrays when nothing changed.
- `scene_progress` must explain whether the scene materially changed.
- `world_state_patch` may omit unchanged fields.
- Treat protagonist identity as frozen unless the patch intentionally refines current situation fields.
- Keep continuity with recent context and relevant lorebook entries.
- Avoid reusing the previous turn's opening image or sentence shape when nothing has advanced.
- `mode=intro`: write the opening scene and end with an immediate hook.
- `mode=turn`: respond directly to the latest player action and produce at least one form of progression:
  - scene advancement
  - thread advancement
  - relationship change
  - new consequential information
  - explicit blockage with concrete consequence
