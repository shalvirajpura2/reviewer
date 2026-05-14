import hmac

from fastapi import APIRouter, Request

from app.core.settings import settings
from app.models.analysis import PublishSummaryRequest
from app.models.review_domain import ReviewCommentPublication
from app.routes.analyze import error_response, resolve_client_key
from app.services.review_publish_service import publish_review_summary


router = APIRouter(prefix="/api", tags=["publishing"])
publish_api_token_header = "x-reviewer-publish-token"


def require_publish_api_token(request: Request) -> None:
    expected_token = settings.reviewer_publish_api_token.strip()
    provided_token = request.headers.get(publish_api_token_header, "").strip()

    if not expected_token:
        raise PermissionError("Reviewer backend publishing requires REVIEWER_PUBLISH_API_TOKEN.")

    if not provided_token or not hmac.compare_digest(provided_token, expected_token):
        raise PermissionError("Reviewer backend publishing token is invalid or missing.")


@router.post("/publish-summary", response_model=ReviewCommentPublication)
async def publish_summary_route(payload: PublishSummaryRequest, request: Request):
    try:
        require_publish_api_token(request)
        return await publish_review_summary(payload.pr_url, resolve_client_key(request), use_backend_publish_token=True)
    except ValueError as error:
        return error_response(request, 400, "invalid_request", str(error))
    except FileNotFoundError as error:
        return error_response(request, 404, "not_found", str(error))
    except PermissionError as error:
        return error_response(request, 403, "forbidden", str(error))
    except ConnectionError as error:
        return error_response(request, 503, "upstream_unavailable", str(error))
