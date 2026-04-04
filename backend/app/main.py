from contextlib import asynccontextmanager
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.routes.analyze import router as analyze_router
from app.routes.stats import router as stats_router
from app.services.github_client import close_github_client

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("reviewer.backend")
started_at = time.time()


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    yield
    await close_github_client()


app = FastAPI(
    title="Reviewer Backend",
    description="Explainable merge confidence analysis for public GitHub pull requests.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def resolve_request_id(request: Request) -> str:
    header_request_id = request.headers.get("x-request-id", "").strip()
    return header_request_id or str(uuid4())


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = resolve_request_id(request)
    request.state.request_id = request_id
    started_request_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started_request_at) * 1000, 1)
        logger.exception(
            "request_failed request_id=%s method=%s path=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = round((time.perf_counter() - started_request_at) * 1000, 1)
    response.headers["X-Request-Id"] = request_id
    logger.info(
        "request_completed request_id=%s method=%s path=%s status_code=%s duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, error: RequestValidationError):
    first_error = error.errors()[0] if error.errors() else None
    message = first_error.get("msg", "Request validation failed.") if isinstance(first_error, dict) else "Request validation failed."
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "validation_failed",
            "message": message,
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, error: Exception):
    logger.exception(
        "unhandled_exception request_id=%s method=%s path=%s error=%s",
        getattr(request.state, "request_id", "unknown"),
        request.method,
        request.url.path,
        type(error).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "internal_error",
            "message": "Reviewer could not complete the request right now.",
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


app.include_router(analyze_router)
app.include_router(stats_router)



@app.get("/health")
async def health_check() -> dict[str, str | bool | int]:
    return {
        "status": "ok",
        "github_token_configured": bool(settings.github_token),
        "database_configured": bool(settings.database_url),
        "uptime_seconds": int(time.time() - started_at),
        "cache_ttl_seconds": settings.cache_ttl_seconds,
        "stale_cache_ttl_seconds": settings.stale_cache_ttl_seconds,
    }
