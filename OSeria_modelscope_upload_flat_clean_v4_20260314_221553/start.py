from __future__ import annotations

import os
from pathlib import Path

import uvicorn


ROOT = Path(__file__).resolve().parent


def read_upload_version() -> str:
    version_file = ROOT / "UPLOAD_VERSION.txt"
    if not version_file.exists():
        return "unknown"
    return version_file.read_text(encoding="utf-8").strip()


def main() -> None:
    os.environ.setdefault("OSERIA_PUBLIC_MODE", "1")
    port = int(os.environ.get("PORT", "7860"))
    print(f"[oseria-upload] version={read_upload_version()}")
    print(f"[oseria-upload] bind port={port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
