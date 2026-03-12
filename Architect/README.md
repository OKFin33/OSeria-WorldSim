# Architect Prototype Layout

`Architect/` is the canonical project root for the active prototype.

## Active Areas

- `api.py`, `service.py`, `api_models.py`, `session_store.py`, `result_packager.py`
  Backend API and orchestration layer
- `interviewer.py`, `interview_controller.py`, `conductor.py`, `forge.py`, `assembler.py`, `llm_client.py`
  Core runtime pipeline
- `data/`
  Core modules, packs, and routing map
- `prompts/`
  Interviewer and subagent prompts
- `frontend/`
  React + TypeScript + Vite frontend shell
- `tests/`
  Backend test suite
- `docs/`
  Active specs, plans, and decision logs
- `docs/OSeria_technical_overview.md`
  Cross-project technical overview for hackathon delivery and internal alignment

## Operational Boundary

If a file is part of the current Architect prototype, it should live under `Architect/`.
Root-level files should be limited to repository metadata and local environment artifacts.
