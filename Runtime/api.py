"""FastAPI app for Runtime vNext."""

from __future__ import annotations

import json
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse

from .api_models import (
    DisplayTitleUpdateRequest,
    ErrorPayload,
    ErrorResponse,
    HealthResponse,
    RuntimeStartRequest,
    RuntimeTurnRequest,
)
from .service import RuntimeService, RuntimeServiceError


def _get_service(app: FastAPI) -> RuntimeService:
    service = getattr(app.state, "runtime_service", None)
    if service is None:
        service = RuntimeService.from_defaults()
        app.state.runtime_service = service
    return cast(RuntimeService, service)


def create_app(service: RuntimeService | None = None) -> FastAPI:
    app = FastAPI(title="OSeria Runtime API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if service is not None:
        app.state.runtime_service = service

    @app.exception_handler(RuntimeServiceError)
    async def handle_runtime_error(_: Request, exc: RuntimeServiceError) -> JSONResponse:
        payload = ErrorResponse(
            error=ErrorPayload(code=exc.code, message=exc.message, retryable=exc.retryable)
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first_error = exc.errors()[0] if exc.errors() else None
        detail = "Invalid request payload."
        if first_error is not None:
            location = ".".join(str(part) for part in first_error.get("loc", []) if part != "body")
            message = str(first_error.get("msg", "Invalid request payload."))
            detail = f"{location}: {message}" if location else message
        payload = ErrorResponse(
            error=ErrorPayload(code="validation_error", message=detail, retryable=False)
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/api/runtime/session")
    async def create_runtime_session(request: RuntimeStartRequest):
        return await _get_service(app).create_session(request)

    @app.post("/api/runtime/turn")
    async def run_runtime_turn(request: RuntimeTurnRequest):
        return await _get_service(app).run_turn(request)

    @app.post("/api/runtime/turn/stream")
    async def run_runtime_turn_stream(request: RuntimeTurnRequest):
        async def event_stream():
            async for event in _get_service(app).stream_turn(request):
                yield _encode_sse(event["event"], event["data"])

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.get("/api/runtime/session/{runtime_session_id}")
    async def get_runtime_session(runtime_session_id: str):
        return _get_service(app).get_session(runtime_session_id)

    @app.get("/api/runtime/session/{runtime_session_id}/debug")
    async def get_runtime_session_debug(runtime_session_id: str):
        return _get_service(app).get_session_debug(runtime_session_id)

    @app.post("/api/runtime/session/{runtime_session_id}/bootstrap")
    async def bootstrap_runtime_session(runtime_session_id: str):
        return await _get_service(app).bootstrap_session(runtime_session_id)

    @app.patch("/api/runtime/session/{runtime_session_id}/display-title")
    async def update_runtime_display_title(runtime_session_id: str, request: DisplayTitleUpdateRequest):
        return _get_service(app).update_display_title(runtime_session_id, request)

    @app.get("/api/runtime/worlds")
    async def list_runtime_worlds():
        return _get_service(app).list_worlds()

    return app


app = create_app()


def _encode_sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
