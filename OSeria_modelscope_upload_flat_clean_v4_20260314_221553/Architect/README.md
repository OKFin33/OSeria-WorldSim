# OSeria Architect

`Architect/` is the world compiler module in OSeria's two-stage system.

## System Role

OSeria is not a character-card workbench. It is a world-card-centered interactive narrative system.

The current system is split into two sibling modules:

- `Architect/`
  Compiles vague user intent into a runnable world.
- `Runtime/`
  Consumes the compiled world and lets it continue growing during play.

Architect is responsible for:

- interview flow
- state convergence
- compile-layer routing
- world delivery
- frozen Runtime handoff

Architect does **not** run the ongoing story loop. That belongs to `Runtime/`.

## Current Output Boundary

Architect currently delivers:

- `blueprint`
- `system_prompt`
- frozen protagonist identity
  - `protagonist_name`
  - `protagonist_gender`
  - `protagonist_identity_brief`

That handoff is the formal boundary into Runtime.

## Current Architecture

Architect's formal architecture is:

1. `State Layer`
2. `Compile Layer`
3. `Delivery Layer`

The active mainline is:

`Interviewer -> Conductor -> Forge -> Assembler -> ResultPackager`

The detailed technical overview lives here:

- [OSeria_technical_overview.md](/Users/okfin3/project/architect-agent-prototype/Architect/docs/OSeria_technical_overview.md)

The active implementation and decision logs live here:

- [implementation_plan.md](/Users/okfin3/project/architect-agent-prototype/Architect/docs/implementation_plan.md)
- [架构Log.md](/Users/okfin3/project/architect-agent-prototype/Architect/docs/logs/架构Log.md)

## Active Areas

- `api.py`, `service.py`, `api_models.py`, `session_store.py`, `result_packager.py`
  Backend API and orchestration layer
- `interviewer.py`, `interview_controller.py`, `conductor.py`, `forge.py`, `assembler.py`, `llm_client.py`
  Core world-compilation pipeline
- `data/`
  Core modules, packs, dimension registry, routing inputs
- `prompts/`
  Interviewer and compile-related prompts
- `frontend/`
  React + TypeScript + Vite frontend shell
- `tests/`
  Backend and frontend validation
- `docs/`
  Specs, plans, logs, and technical overview

## Repo Boundary

`Architect/` is no longer the canonical root for the whole prototype.

The current repository contains at least:

- [Architect](/Users/okfin3/project/architect-agent-prototype/Architect)
- [Runtime](/Users/okfin3/project/architect-agent-prototype/Runtime)

If you need system-level understanding, do not read this module in isolation.
Use:

- [Architect/docs/OSeria_technical_overview.md](/Users/okfin3/project/architect-agent-prototype/Architect/docs/OSeria_technical_overview.md)
- [Runtime/docs/implementation_plan.md](/Users/okfin3/project/architect-agent-prototype/Runtime/docs/implementation_plan.md)

## Operational Note

If code, README, plans, and logs disagree:

1. trust the current code
2. then update the docs

Document drift is not a feature.
