from fastapi import APIRouter, Request

from app.models.analysis import PublishSummaryRequest
from app.models.review_domain import ReviewCommentPublication
from app.routes.analyze import error_response, resolve_client_key
from app.services.review_publish_service import publish_review_summary


router = APIRouter(prefix="/api", tags=["publishing"])


@router.post("/publish-summary", response_model=ReviewCommentPublication)
async def publish_summary_route(payload: PublishSummaryRequest, request: Request):
    try:
        return await publish_review_summary(payload.pr_url, resolve_client_key(request), use_backend_publish_token=True)
    except ValueError as error:
        return error_response(request, 400, "invalid_request", str(error))
    except FileNotFoundError as error:
        return error_response(request, 404, "not_found", str(error))
    except PermissionError as error:
        return error_response(request, 403, "forbidden", str(error))
    except ConnectionError as error:
        return error_response(request, 503, "upstream_unavailable", str(error))
