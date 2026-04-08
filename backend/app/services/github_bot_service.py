from app.models.github_bot import (
    GithubBotPullRequestSummary,
    GithubBotPullRequestsResponse,
    GithubBotRepositoriesResponse,
    GithubBotRepositorySettings,
    GithubBotRepositorySummary,
)
from app.services.github_app_auth import (
    fetch_app_installations,
    fetch_installation_access_token_by_id,
    fetch_installation_repositories,
    fetch_repo_installation_id,
    github_app_is_configured,
)
from app.services.github_bot_settings_store import load_repository_settings, save_repository_settings
from app.services.github_client import fetch_open_pull_requests


async def list_connected_repositories() -> GithubBotRepositoriesResponse:
    if not github_app_is_configured():
        raise PermissionError("Reviewer GitHub App is not configured on the backend.")

    repositories: list[GithubBotRepositorySummary] = []
    seen_full_names: set[str] = set()

    for installation in await fetch_app_installations():
        installation_id = int(installation.get("id") or 0)
        if not installation_id:
            continue

        installation_repositories = await fetch_installation_repositories(installation_id)
        installation_token = await fetch_installation_access_token_by_id(installation_id)

        for repository in installation_repositories:
            full_name = str(repository.get("full_name") or "")
            if not full_name or full_name.lower() in seen_full_names:
                continue

            owner_login = str(repository.get("owner", {}).get("login") or full_name.split("/")[0])
            repo_name = str(repository.get("name") or full_name.split("/")[-1])
            settings = load_repository_settings(owner_login, repo_name)
            open_pull_requests = await fetch_open_pull_requests(owner_login, repo_name, github_token=installation_token)
            repositories.append(
                GithubBotRepositorySummary(
                    owner=owner_login,
                    repo=repo_name,
                    full_name=full_name,
                    installation_id=installation_id,
                    default_branch=str(repository.get("default_branch") or "main"),
                    open_pull_requests=len(open_pull_requests),
                    settings=settings,
                )
            )
            seen_full_names.add(full_name.lower())

    repositories.sort(key=lambda repository: repository.full_name.lower())
    return GithubBotRepositoriesResponse(repositories=repositories)


async def list_repository_pull_requests(owner: str, repo: str) -> GithubBotPullRequestsResponse:
    installation_id = await fetch_repo_installation_id({"owner": owner, "repo": repo, "pull_number": 0})
    installation_token = await fetch_installation_access_token_by_id(installation_id)
    settings = load_repository_settings(owner, repo)
    pull_requests = await fetch_open_pull_requests(owner, repo, github_token=installation_token)

    repository = GithubBotRepositorySummary(
        owner=owner,
        repo=repo,
        full_name=f"{owner}/{repo}",
        installation_id=installation_id,
        default_branch="main",
        open_pull_requests=len(pull_requests),
        settings=settings,
    )

    return GithubBotPullRequestsResponse(
        repository=repository,
        pull_requests=[
            GithubBotPullRequestSummary(
                number=int(pull_request.get("number") or 0),
                title=str(pull_request.get("title") or "Untitled pull request"),
                author=str(pull_request.get("user", {}).get("login") or "unknown"),
                updated_at=str(pull_request.get("updated_at") or ""),
                html_url=str(pull_request.get("html_url") or ""),
                base_branch=str(pull_request.get("base", {}).get("ref") or "main"),
                head_branch=str(pull_request.get("head", {}).get("ref") or ""),
                draft=bool(pull_request.get("draft") or False),
                mode=repository_settings_mode(settings),
            )
            for pull_request in pull_requests
        ],
    )


def repository_settings_mode(settings: GithubBotRepositorySettings) -> str:
    if settings.automatic_review and settings.review_new_pushes:
        return "review_new_pushes"

    if settings.automatic_review:
        return "automatic_review"

    return "manual_review"


def get_repository_settings(owner: str, repo: str) -> GithubBotRepositorySettings:
    return load_repository_settings(owner, repo)


def update_repository_settings(owner: str, repo: str, settings: GithubBotRepositorySettings) -> GithubBotRepositorySettings:
    return save_repository_settings(owner, repo, settings)
