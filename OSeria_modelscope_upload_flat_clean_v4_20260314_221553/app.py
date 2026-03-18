from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from Architect.api import create_app as create_architect_app
from Runtime.api import create_app as create_runtime_app


ROOT = Path(__file__).resolve().parent
ARCHITECT_DIST = ROOT / "Architect" / "frontend" / "dist"
RUNTIME_DIST = ROOT / "Runtime" / "frontend" / "dist"


def ensure_dist(path: Path, label: str) -> None:
    if not (path / "index.html").exists():
        raise RuntimeError(f"{label} dist is missing at {path}. Run ./build_frontends.sh first.")


def resolve_dist_file(dist_dir: Path, relative_path: str) -> Path:
    candidate = (dist_dir / relative_path).resolve()
    dist_root = dist_dir.resolve()
    if not candidate.is_file() or dist_root not in candidate.parents:
        raise HTTPException(status_code=404, detail="Not found")
    return candidate


def create_upload_app() -> FastAPI:
    os.environ.setdefault("OSERIA_PUBLIC_MODE", "1")
    ensure_dist(ARCHITECT_DIST, "Architect frontend")
    ensure_dist(RUNTIME_DIST, "Runtime frontend")

    app = FastAPI(
        title="OSeria Upload App",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    app.mount("/architect-api", create_architect_app(), name="architect-api")
    app.mount("/runtime-api", create_runtime_app(), name="runtime-api")
    app.mount("/assets", StaticFiles(directory=ARCHITECT_DIST / "assets"), name="architect-assets")
    app.mount("/runtime/assets", StaticFiles(directory=RUNTIME_DIST / "assets"), name="runtime-assets")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    async def architect_index() -> FileResponse:
        return FileResponse(ARCHITECT_DIST / "index.html")

    @app.get("/{file_path:path}")
    async def architect_root_files(file_path: str) -> FileResponse:
        if not file_path or "/" in file_path or "." not in file_path:
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(resolve_dist_file(ARCHITECT_DIST, file_path))

    @app.get("/runtime")
    async def runtime_redirect() -> RedirectResponse:
        return RedirectResponse(url="/runtime/")

    @app.get("/runtime/")
    async def runtime_index() -> FileResponse:
        return FileResponse(RUNTIME_DIST / "index.html")

    return app


app = create_upload_app()
