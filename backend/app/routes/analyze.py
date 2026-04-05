from ipaddress import ip_address

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.models.analysis import AnalyzeRequest, PrAnalysisResult, PreviewRequest, PrPreviewResult
from app.services.analysis_service import analyze_pull_request, preview_pull_request


router = APIRouter(prefix="/api", tags=["analysis"])


def error_response(request: Request, status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


def is_trusted_proxy_host(client_host: str) -> bool:
    try:
        client_ip = ip_address(client_host)
    except ValueError:
        return False

    return any(client_ip in trusted_proxy_network for trusted_proxy_network in settings.trusted_proxy_cidrs)


def resolve_client_key(request: Request) -> str:
    direct_client_ip = request.client.host.strip() if request.client and request.client.host else ""
    forwarded_for = request.headers.get("x-forwarded-for", "")

    if direct_client_ip and is_trusted_proxy_host(direct_client_ip):
        for forwarded_part in [item.strip() for item in forwarded_for.split(",") if item.strip()]:
            try:
                return str(ip_address(forwarded_part))
            except ValueError:
                continue

    return direct_client_ip or "anonymous"


@router.post("/preview", response_model=PrPreviewResult)
async def preview_route(payload: PreviewRequest, request: Request):
    try:
        return await preview_pull_request(payload.pr_url, resolve_client_key(request))
    except ValueError as error:
        return error_response(request, 400, "invalid_request", str(error))
    except FileNotFoundError as error:
        return error_response(request, 404, "not_found", str(error))
    except PermissionError as error:
        return error_response(
            request,
            429,
            "rate_limited",
            str(error) or "GitHub is temporarily rate limited for this preview. Please try again in a few minutes.",
        )
    except ConnectionError as error:
        return error_response(request, 503, "upstream_unavailable", str(error))


@router.post("/analyze", response_model=PrAnalysisResult)
async def analyze_route(payload: AnalyzeRequest, request: Request):
    try:
        return await analyze_pull_request(payload.pr_url, resolve_client_key(request), payload.force_refresh)
    except ValueError as error:
        return error_response(request, 400, "invalid_request", str(error))
    except FileNotFoundError as error:
        return error_response(request, 404, "not_found", str(error))
    except PermissionError as error:
        return error_response(
            request,
            429,
            "rate_limited",
            str(error) or "GitHub is temporarily rate limited for this analysis. Please try again in a few minutes.",
        )
    except ConnectionError as error:
        return error_response(request, 503, "upstream_unavailable", str(error))
