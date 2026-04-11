import asyncio
from datetime import datetime, timezone

from app.models.github_bot import (
    GithubBotPullRequestSummary,
    GithubBotPullRequestsResponse,
    GithubBotRepositoriesResponse,
    GithubBotRepositoryActivity,
    GithubBotRepositorySettings,
    GithubBotRepositorySummary,
)
from app.models.review_domain import ReviewCommentPublication
from app.services.github_app_auth import (
    fetch_app_installations,
    fetch_installation_access_token_by_id,
    fetch_installation_repositories,
    fetch_repo_installation_id,
    github_app_is_configured,
)
from app.services.github_bot_settings_store import (
    load_repository_activity,
    load_repository_settings,
    save_repository_activity,
    save_repository_settings,
)
from app.services.github_client import fetch_open_pull_requests, fetch_repository_metadata, fetch_user_repositories
from app.services.review_publish_service import publish_review_summary


async def fetch_accessible_repository_map(github_token: str) -> dict[str, dict[str, object]]:
    repositories = await fetch_user_repositories(github_token)
    return {
        str(repository.get("full_name") or "").lower(): repository
        for repository in repositories
        if isinstance(repository, dict) and repository.get("full_name")
    }


def build_repository_summary(
    repository: dict[str, object],
    installation_id: int,
    open_pull_request_count: int,
) -> GithubBotRepositorySummary:
    full_name = str(repository.get("full_name") or "")
    owner_login = str(repository.get("owner", {}).get("login") or full_name.split("/")[0])
    repo_name = str(repository.get("name") or full_name.split("/")[-1])
    settings = load_repository_settings(owner_login, repo_name)
    activity = load_repository_activity(owner_login, repo_name)

    return GithubBotRepositorySummary(
        owner=owner_login,
        repo=repo_name,
        full_name=full_name,
        installation_id=installation_id,
        default_branch=str(repository.get("default_branch") or "main"),
        open_pull_requests=open_pull_request_count,
        settings=settings,
        activity=activity,
    )


async def fetch_repository_open_pull_request_count(
    repository: dict[str, object],
    installation_id: int,
    installation_token: str,
    semaphore: asyncio.Semaphore,
) -> GithubBotRepositorySummary:
    full_name = str(repository.get("full_name") or "")
    owner_login = str(repository.get("owner", {}).get("login") or full_name.split("/")[0])
    repo_name = str(repository.get("name") or full_name.split("/")[-1])

    async with semaphore:
        open_pull_requests = await fetch_open_pull_requests(owner_login, repo_name, github_token=installation_token)

    return build_repository_summary(repository, installation_id, len(open_pull_requests))


async def ensure_repository_access(owner: str, repo: str, github_token: str) -> None:
    accessible_repositories = await fetch_accessible_repository_map(github_token)
    if f"{owner}/{repo}".lower() not in accessible_repositories:
        raise PermissionError("That repository is not available in your connected GitHub workspace.")


async def list_connected_repositories(github_token: str) -> GithubBotRepositoriesResponse:
    if not github_app_is_configured():
        raise PermissionError("Reviewer GitHub App is not configured on the backend.")

    repositories: list[GithubBotRepositorySummary] = []
    seen_full_names: set[str] = set()
    accessible_repositories = await fetch_accessible_repository_map(github_token)
    semaphore = asyncio.Semaphore(8)

    for installation in await fetch_app_installations():
        installation_id = int(installation.get("id") or 0)
        if not installation_id:
            continue

        installation_repositories = await fetch_installation_repositories(installation_id)
        installation_token = await fetch_installation_access_token_by_id(installation_id)
        visible_repositories = [
            repository for repository in installation_repositories
            if str(repository.get("full_name") or "").lower() in accessible_repositories
        ]
        repository_summaries = await asyncio.gather(
            *[
                fetch_repository_open_pull_request_count(repository, installation_id, installation_token, semaphore)
                for repository in visible_repositories
                if str(repository.get("full_name") or "").lower() not in seen_full_names
            ]
        )

        for repository_summary in repository_summaries:
            full_name = repository_summary.full_name
            if not full_name or full_name.lower() in seen_full_names:
                continue

            repositories.append(repository_summary)
            seen_full_names.add(full_name.lower())

    repositories.sort(key=lambda repository: repository.full_name.lower())
    return GithubBotRepositoriesResponse(repositories=repositories)


async def list_repository_pull_requests(owner: str, repo: str, github_token: str) -> GithubBotPullRequestsResponse:
    await ensure_repository_access(owner, repo, github_token)
    installation_id = await fetch_repo_installation_id({"owner": owner, "repo": repo, "pull_number": 0})
    installation_token = await fetch_installation_access_token_by_id(installation_id)
    settings = load_repository_settings(owner, repo)
    activity = load_repository_activity(owner, repo)
    pull_requests = await fetch_open_pull_requests(owner, repo, github_token=installation_token)
    repository_metadata = await fetch_repository_metadata(owner, repo, github_token=installation_token)

    repository = GithubBotRepositorySummary(
        owner=owner,
        repo=repo,
        full_name=f"{owner}/{repo}",
        installation_id=installation_id,
        default_branch=str(repository_metadata.get("default_branch") or "main"),
        open_pull_requests=len(pull_requests),
        settings=settings,
        activity=activity,
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

    if not settings.manual_review:
        return "disabled"

    return "manual_review"


async def get_repository_settings(owner: str, repo: str, github_token: str) -> GithubBotRepositorySettings:
    await ensure_repository_access(owner, repo, github_token)
    return load_repository_settings(owner, repo)


async def update_repository_settings(owner: str, repo: str, settings: GithubBotRepositorySettings, github_token: str) -> GithubBotRepositorySettings:
    await ensure_repository_access(owner, repo, github_token)
    return save_repository_settings(owner, repo, settings)


def build_pull_request_url(owner: str, repo: str, pull_number: int) -> str:
    return f"https://github.com/{owner}/{repo}/pull/{pull_number}"


def build_repository_activity(
    pull_number: int,
    trigger_source: str,
    publication: ReviewCommentPublication,
) -> GithubBotRepositoryActivity:
    return GithubBotRepositoryActivity(
        last_review_at=datetime.now(timezone.utc).isoformat(),
        last_pull_number=pull_number,
        last_trigger=trigger_source,
        last_action=publication.action,
        last_comment_url=publication.html_url,
    )


def record_repository_activity(
    owner: str,
    repo: str,
    pull_number: int,
    trigger_source: str,
    publication: ReviewCommentPublication,
) -> GithubBotRepositoryActivity:
    return save_repository_activity(owner, repo, build_repository_activity(pull_number, trigger_source, publication))


async def trigger_manual_review(
    owner: str,
    repo: str,
    pull_number: int,
    client_key: str,
    github_token: str | None = None,
    trigger_source: str = "manual_review",
):
    if github_token:
        await ensure_repository_access(owner, repo, github_token)
    repository_settings = load_repository_settings(owner, repo)
    if trigger_source == "manual_review" and not repository_settings.manual_review:
        raise ValueError("Manual review is turned off for this repository. Enable it in the dashboard before posting a summary.")
    publication = await publish_review_summary(
        build_pull_request_url(owner, repo, pull_number),
        client_key,
        use_backend_publish_token=True,
    )
    record_repository_activity(owner, repo, pull_number, trigger_source, publication)
    return publication
