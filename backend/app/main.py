from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.routes.analyze import router as analyze_router
from app.routes.stats import router as stats_router

app = FastAPI(
    title="Reviewer Backend",
    description="Explainable merge confidence analysis for public GitHub pull requests.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, error: RequestValidationError):
    first_error = error.errors()[0] if error.errors() else None
    message = first_error.get("msg", "Request validation failed.") if isinstance(first_error, dict) else "Request validation failed."
    return JSONResponse(status_code=422, content={"error_code": "validation_failed", "message": message})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, _error: Exception):
    return JSONResponse(
        status_code=500,
        content={"error_code": "internal_error", "message": "Reviewer could not complete the request right now."},
    )


app.include_router(analyze_router)
app.include_router(stats_router)


@app.get("/health")
async def health_check() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "github_token_configured": bool(settings.github_token),
        "database_configured": bool(settings.database_url),
    }
