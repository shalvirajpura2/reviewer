from ipaddress import ip_address

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models.analysis import AnalyzeRequest, PrAnalysisResult, PreviewRequest, PrPreviewResult
from app.services.analysis_service import analyze_pull_request, preview_pull_request


router = APIRouter(prefix="/api", tags=["analysis"])


def resolve_client_key(request: Request) -> str:
    direct_client_ip = request.client.host.strip() if request.client and request.client.host else ""
    trusted_client_ip = direct_client_ip
    forwarded_for = request.headers.get("x-forwarded-for", "")

    try:
        remote_ip = ip_address(direct_client_ip) if direct_client_ip else None
    except ValueError:
        remote_ip = None

    if remote_ip and (remote_ip.is_loopback or remote_ip.is_private or remote_ip.is_link_local):
        for forwarded_part in [item.strip() for item in forwarded_for.split(",") if item.strip()]:
            try:
                trusted_client_ip = str(ip_address(forwarded_part))
                break
            except ValueError:
                continue

    base_client_key = trusted_client_ip or direct_client_ip or "anonymous"


    return base_client_key


@router.post("/preview", response_model=PrPreviewResult)
async def preview_route(payload: PreviewRequest, request: Request):
    try:
        return await preview_pull_request(payload.pr_url, resolve_client_key(request))
    except ValueError as error:
        return JSONResponse(status_code=400, content={"error_code": "invalid_request", "message": str(error)})
    except FileNotFoundError as error:
        return JSONResponse(status_code=404, content={"error_code": "not_found", "message": str(error)})
    except PermissionError as error:
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "rate_limited",
                "message": str(error) or "GitHub is temporarily rate limited for this preview. Please try again in a few minutes.",
            },
        )
    except ConnectionError as error:
        return JSONResponse(status_code=503, content={"error_code": "upstream_unavailable", "message": str(error)})
    except Exception:
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "preview_failed",
                "message": "Reviewer could not load that pull request preview right now.",
            },
        )


@router.post("/analyze", response_model=PrAnalysisResult)
async def analyze_route(payload: AnalyzeRequest, request: Request):
    try:
        return await analyze_pull_request(payload.pr_url, resolve_client_key(request), payload.force_refresh)
    except ValueError as error:
        return JSONResponse(status_code=400, content={"error_code": "invalid_request", "message": str(error)})
    except FileNotFoundError as error:
        return JSONResponse(status_code=404, content={"error_code": "not_found", "message": str(error)})
    except PermissionError as error:
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "rate_limited",
                "message": str(error) or "GitHub is temporarily rate limited for this analysis. Please try again in a few minutes.",
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
