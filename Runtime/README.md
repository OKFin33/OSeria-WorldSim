# OSeria Runtime vNext

`Runtime/` is the standalone story-running module that consumes Architect vNext output and turns it into a playable interactive fiction loop.

## Responsibilities

- Accept `system_prompt` and blueprint metadata from Architect
- Create and persist runtime sessions
- Generate intro and turn-by-turn narrative responses
- Maintain a lightweight world-state snapshot
- Extract and upsert lorebook entries every 5 turns by default
- Expose a dedicated Runtime frontend with chat, world list, and details drawers

## Local Run

Backend:

```bash
python -m Runtime.main
```

Frontend:

```bash
cd Runtime/frontend
npm install
npm run dev
```
