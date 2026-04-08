from fastapi import APIRouter, Request

from app.models.github_bot import GithubBotPullRequestsResponse, GithubBotRepositoriesResponse, GithubBotRepositorySettings, GithubBotRepositorySettingsUpdate
from app.routes.analyze import error_response
from app.services.github_bot_service import get_repository_settings, list_connected_repositories, list_repository_pull_requests, update_repository_settings


router = APIRouter(prefix="/api/github-bot", tags=["github-bot"])


@router.get("/repositories", response_model=GithubBotRepositoriesResponse)
async def list_connected_repositories_route(request: Request):
    try:
        return await list_connected_repositories()
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
        return await list_repository_pull_requests(owner, repo)
    except PermissionError as error:
        return error_response(request, 403, "forbidden", str(error))
    except FileNotFoundError as error:
        return error_response(request, 404, "not_found", str(error))
    except ValueError as error:
        return error_response(request, 400, "invalid_request", str(error))
    except ConnectionError as error:
        return error_response(request, 503, "upstream_unavailable", str(error))


@router.get("/repositories/{owner}/{repo}/settings", response_model=GithubBotRepositorySettings)
async def get_repository_settings_route(owner: str, repo: str):
    return get_repository_settings(owner, repo)


@router.put("/repositories/{owner}/{repo}/settings", response_model=GithubBotRepositorySettings)
async def update_repository_settings_route(owner: str, repo: str, payload: GithubBotRepositorySettingsUpdate):
    return update_repository_settings(owner, repo, GithubBotRepositorySettings(**payload.model_dump()))
