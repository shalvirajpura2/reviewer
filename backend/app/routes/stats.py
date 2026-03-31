from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.stats import PublicStatsResponse, RecentAnalysesResponse, RecordVisitRequest, RepoStarsResponse
from app.services.stats_service import get_cached_repo_stars, get_public_stats, get_recent_analyses, record_visit

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=PublicStatsResponse)
async def get_stats_route() -> PublicStatsResponse:
    try:
        return PublicStatsResponse(**get_public_stats())
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"error_code": "stats_unavailable", "message": "Reviewer stats are temporarily unavailable."},
        )


@router.get("/recent-analyses", response_model=RecentAnalysesResponse)
async def get_recent_analyses_route() -> RecentAnalysesResponse:
    try:
        return RecentAnalysesResponse(items=get_recent_analyses())
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"error_code": "recent_analyses_unavailable", "message": "Reviewer could not load recent analyses right now."},
        )


@router.post("/visit", response_model=PublicStatsResponse)
async def record_visit_route(payload: RecordVisitRequest) -> PublicStatsResponse:
    try:
        return PublicStatsResponse(**record_visit(payload.client_id))
    except ValueError as error:
        return JSONResponse(
            status_code=400,
            content={"error_code": "invalid_visit", "message": str(error)},
        )
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"error_code": "visit_unavailable", "message": "Reviewer visit stats are temporarily unavailable."},
        )


@router.get("/repo-stars", response_model=RepoStarsResponse)
async def get_repo_stars_route():
    try:
        stars = await get_cached_repo_stars("shalvirajpura2", "reviewer")
        return RepoStarsResponse(stars=stars)
    except PermissionError:
        return JSONResponse(
            status_code=503,
            content={
                "error_code": "github_temporarily_unavailable",
                "message": "GitHub is temporarily unavailable for repository stats. Please try again shortly.",
            },
        )
    except ConnectionError:
        return JSONResponse(
            status_code=503,
            content={
                "error_code": "github_unavailable",
                "message": "GitHub is temporarily unavailable for repository stats. Please try again shortly.",
            },
        )
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "error_code": "repo_stars_unavailable",
                "message": "Reviewer could not load GitHub stars right now.",
            },
        )
