#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

cd "$ROOT/Architect/frontend"
npm ci
npm run build

cd "$ROOT/Runtime/frontend"
npm ci
npm run build

echo "[oseria-upload] frontends built"
