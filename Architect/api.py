"""FastAPI app for the Architect engine."""

from __future__ import annotations

from typing import cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api_models import ErrorPayload, ErrorResponse, GenerateRequest, HealthResponse, InterviewMessageRequest
from .service import ArchitectService, ArchitectServiceError


def _get_service(app: FastAPI) -> ArchitectService:
    service = getattr(app.state, "architect_service", None)
    if service is None:
        service = ArchitectService.from_defaults()
        app.state.architect_service = service
    return cast(ArchitectService, service)


def create_app(service: ArchitectService | None = None) -> FastAPI:
    app = FastAPI(title="OSeria Architect API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if service is not None:
        app.state.architect_service = service

    @app.exception_handler(ArchitectServiceError)
    async def handle_architect_error(_: Request, exc: ArchitectServiceError) -> JSONResponse:
        payload = ErrorResponse(
            error=ErrorPayload(code=exc.code, message=exc.message, retryable=exc.retryable)
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/api/interview/start")
    async def start_interview():
        return await _get_service(app).start_interview()

    @app.post("/api/interview/message")
    async def submit_interview_message(request: InterviewMessageRequest):
        return await _get_service(app).submit_interview_message(request)

    @app.post("/api/generate")
    async def generate_world(request: GenerateRequest):
        return await _get_service(app).generate_world(request)

    return app


app = create_app()
