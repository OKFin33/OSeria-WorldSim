# OSeria Upload Bundle

This is a clean upload-oriented bundle for OSeria.

It contains:

- `Architect/`
  - world interview, compile, delivery
- `Runtime/`
  - playable runtime loop

This bundle intentionally excludes local development debris:

- docs
- tests
- local logs
- `.runtime_sessions/`
- workspace `.git`

## What is included

- Python backend source for `Architect` and `Runtime`
- React frontend source for both modules
- unified root startup script
- unified root requirements file
- environment template

## Quick start

1. Create and activate a virtual environment.
2. Install Python dependencies.
3. Install frontend dependencies and build both frontends.
4. Start the single-port root app.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

./build_frontends.sh
python start.py
```

Default single-port local run:

- App: `7860`

Mounted paths:

- Architect UI: `/`
- Runtime UI: `/runtime/`
- Architect API: `/architect-api`
- Runtime API: `/runtime-api`

## Environment

Copy `.env.example` to `.env` and fill in at least the model credentials you intend to use.

Architect and Runtime both read the root `.env`.

## Notes

- Architect frontend production build does not expose the dev replay UI.
- This upload bundle keeps frontend source for maintainability, but runtime/debug history is not included.
- This upload build is single-port by design, which is suitable for hosted Studio-style environments.
