from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models.stats import PublicStatsResponse, RecentAnalysesResponse, RecordVisitRequest, RepoStarsResponse
from app.services.stats_service import get_cached_repo_stars, get_public_stats, get_recent_analyses, record_visit

router = APIRouter(prefix="/api/stats", tags=["stats"])


def error_response(request: Request, status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


@router.get("", response_model=PublicStatsResponse)
async def get_stats_route() -> PublicStatsResponse:
    return PublicStatsResponse(**get_public_stats())


@router.get("/recent-analyses", response_model=RecentAnalysesResponse)
async def get_recent_analyses_route() -> RecentAnalysesResponse:
    return RecentAnalysesResponse(items=get_recent_analyses())


@router.post("/visit", response_model=PublicStatsResponse)
async def record_visit_route(payload: RecordVisitRequest, request: Request) -> PublicStatsResponse:
    try:
        return PublicStatsResponse(**record_visit(payload.client_id))
    except ValueError as error:
        return error_response(request, 400, "invalid_visit", str(error))


@router.get("/repo-stars", response_model=RepoStarsResponse)
async def get_repo_stars_route(request: Request):
    try:
        stars = await get_cached_repo_stars("shalvirajpura2", "reviewer")
        return RepoStarsResponse(stars=stars)
    except PermissionError:
        return error_response(
            request,
            503,
            "github_temporarily_unavailable",
            "GitHub is temporarily unavailable for repository stats. Please try again shortly.",
        )
    except ConnectionError:
        return error_response(
            request,
            503,
            "github_unavailable",
            "GitHub is temporarily unavailable for repository stats. Please try again shortly.",
        )