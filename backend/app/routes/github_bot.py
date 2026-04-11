from fastapi import APIRouter, Request

from app.models.github_bot import (
    GithubBotManualReviewRequest,
    GithubBotPullRequestsResponse,
    GithubBotRepositoriesResponse,
    GithubBotRepositorySettings,
    GithubBotRepositorySettingsUpdate,
    GithubBotWebhookResult,
)
from app.models.review_domain import ReviewCommentPublication
from app.routes.analyze import error_response, resolve_client_key
from app.routes.auth import require_web_csrf
from app.services.github_bot_service import (
    get_repository_settings,
    list_connected_repositories,
    list_repository_pull_requests,
    trigger_manual_review,
    update_repository_settings,
)
from app.services.github_webhook_service import handle_github_webhook
from app.services.web_auth_session_service import github_session_cookie_name, require_web_auth_session


router = APIRouter(prefix="/api/github-bot", tags=["github-bot"])


@router.get("/repositories", response_model=GithubBotRepositoriesResponse)
async def list_connected_repositories_route(request: Request):
    try:
        session = require_web_auth_session(request.cookies.get(github_session_cookie_name))
        return await list_connected_repositories(session.access_token)
    except PermissionError as error:
        return error_response(request, 403, "forbidden", str(error))
    except FileNotFoundError as error:
        return error_response(request, 404, "not_found", str(error))
    except ValueError as error:
        return error_response(request, 400, "invalid_request", str(error))
    except ConnectionError as error:
        return error_response(request, 503, "upstream_unavailable", str(error))


@router.get("/repositories/{owner}/{repo}/pulls", response_model=GithubBotPullRequestsResponse)
async def list_repository_pull_requests_route(owner: str, repo: str, request: Request):
    try:
        session = require_web_auth_session(request.cookies.get(github_session_cookie_name))
        return await list_repository_pull_requests(owner, repo, session.access_token)
    except PermissionError as error:
        return error_response(request, 403, "forbidden", str(error))
    except FileNotFoundError as error:
        return error_response(request, 404, "not_found", str(error))
    except ValueError as error:
        return error_response(request, 400, "invalid_request", str(error))
    except ConnectionError as error:
        return error_response(request, 503, "upstream_unavailable", str(error))


@router.get("/repositories/{owner}/{repo}/settings", response_model=GithubBotRepositorySettings)
async def get_repository_settings_route(owner: str, repo: str, request: Request):
    try:
        session = require_web_auth_session(request.cookies.get(github_session_cookie_name))
        return await get_repository_settings(owner, repo, session.access_token)
    except PermissionError as error:
        return error_response(request, 403, "forbidden", str(error))
    except FileNotFoundError as error:
        return error_response(request, 404, "not_found", str(error))
    except ValueError as error:
        return error_response(request, 400, "invalid_request", str(error))
    except ConnectionError as error:
        return error_response(request, 503, "upstream_unavailable", str(error))


@router.put("/repositories/{owner}/{repo}/settings", response_model=GithubBotRepositorySettings)
async def update_repository_settings_route(owner: str, repo: str, payload: GithubBotRepositorySettingsUpdate, request: Request):
    try:
        require_web_csrf(request)
        session = require_web_auth_session(request.cookies.get(github_session_cookie_name))
        return await update_repository_settings(owner, repo, GithubBotRepositorySettings(**payload.model_dump()), session.access_token)
    except PermissionError as error:
        return error_response(request, 403, "forbidden", str(error))
    except FileNotFoundError as error:
        return error_response(request, 404, "not_found", str(error))
    except ValueError as error:
        return error_response(request, 400, "invalid_request", str(error))
    except ConnectionError as error:
        return error_response(request, 503, "upstream_unavailable", str(error))


@router.post("/repositories/{owner}/{repo}/review", response_model=ReviewCommentPublication)
async def trigger_manual_review_route(owner: str, repo: str, payload: GithubBotManualReviewRequest, request: Request):
    try:
        require_web_csrf(request)
        session = require_web_auth_session(request.cookies.get(github_session_cookie_name))
        return await trigger_manual_review(owner, repo, payload.pull_number, resolve_client_key(request), session.access_token)
    except PermissionError as error:
        return error_response(request, 403, "forbidden", str(error))
    except FileNotFoundError as error:
        return error_response(request, 404, "not_found", str(error))
    except ValueError as error:
        return error_response(request, 400, "invalid_request", str(error))
    except ConnectionError as error:
        return error_response(request, 503, "upstream_unavailable", str(error))


@router.post("/webhooks/github", response_model=GithubBotWebhookResult)
async def github_webhook_route(request: Request):
    try:
        payload = await request.body()
        return await handle_github_webhook(
            payload,
            request.headers.get("x-github-event", ""),
            request.headers.get("x-hub-signature-256", ""),
            request.headers.get("x-github-delivery", ""),
        )
    except PermissionError as error:
        return error_response(request, 403, "forbidden", str(error))
    except ValueError as error:
        return error_response(request, 400, "invalid_request", str(error))
    except FileNotFoundError as error:
        return error_response(request, 404, "not_found", str(error))
    except ConnectionError as error:
        return error_response(request, 503, "upstream_unavailable", str(error))
