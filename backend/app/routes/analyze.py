from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.analysis import AnalyzeRequest, PrAnalysisResult
from app.services.analysis_service import analyze_pull_request


router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze", response_model=PrAnalysisResult)
async def analyze_route(payload: AnalyzeRequest):
    try:
        return await analyze_pull_request(payload.pr_url)
    except ValueError as error:
        return JSONResponse(status_code=400, content={"error_code": "invalid_request", "message": str(error)})
    except FileNotFoundError as error:
        return JSONResponse(status_code=404, content={"error_code": "not_found", "message": str(error)})
    except PermissionError:
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "rate_limited",
                "message": "GitHub is temporarily rate limited for this analysis. Please try again in a few minutes.",
            },
        )
    except ConnectionError as error:
        return JSONResponse(status_code=503, content={"error_code": "upstream_unavailable", "message": str(error)})
    except Exception:
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "analysis_failed",
                "message": "Reviewer could not complete the analysis right now.",
            },
        )
