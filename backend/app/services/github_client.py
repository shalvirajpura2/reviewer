from typing import Any

import httpx

from app.core.settings import settings
from app.models.analysis import ChangedFile, GithubCommitSummary, GithubPrMetadata

max_pr_file_pages = 30



def build_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "reviewer-v1",
    }

    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    return headers


async def github_fetch(path: str) -> Any:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{settings.github_api_base}{path}", headers=build_headers())
    except httpx.TimeoutException as error:
        raise ConnectionError("GitHub took too long to respond. Please try again.") from error
    except httpx.HTTPError as error:
        raise ConnectionError("GitHub could not be reached from the analysis service.") from error

    if response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0":
        raise PermissionError("GitHub rate limit reached. Add a GITHUB_TOKEN or try again later.")

    if response.status_code == 403 and "secondary rate limit" in response.text.lower():
        raise PermissionError("GitHub temporarily rate limited this analysis. Please retry shortly.")

    if response.status_code == 404:
        raise FileNotFoundError("Repository or pull request not found, or the PR is not public.")

    if response.status_code in {502, 503, 504}:
        raise ConnectionError("GitHub is temporarily unavailable. Please try again.")

    if response.status_code >= 400:
        raise ValueError("GitHub returned an unexpected response while fetching the pull request.")

    return response.json()


async def fetch_pr_metadata(parsed_pr: dict[str, str | int]) -> GithubPrMetadata:
    payload = await github_fetch(
        f"/repos/{parsed_pr['owner']}/{parsed_pr['repo']}/pulls/{parsed_pr['pull_number']}"
    )

    return GithubPrMetadata(
        owner=str(parsed_pr["owner"]),
        repo=str(parsed_pr["repo"]),
        pull_number=int(parsed_pr["pull_number"]),
        repo_full_name=payload["base"]["repo"]["full_name"],
        title=payload["title"],
        author=payload["user"]["login"],
        author_avatar_url=payload["user"]["avatar_url"],
        base_branch=payload["base"]["ref"],
        head_branch=payload["head"]["ref"],
        head_sha=payload.get("head", {}).get("sha", ""),
        commits=payload["commits"],
        additions=payload["additions"],
        deletions=payload["deletions"],
        changed_files=payload["changed_files"],
        html_url=payload["html_url"],
        created_at=payload["created_at"],
        updated_at=payload["updated_at"],
    )


async def fetch_pr_files(
    parsed_pr: dict[str, str | int],
    expected_file_count: int | None = None,
) -> tuple[list[ChangedFile], list[str]]:
    collected_files: list[ChangedFile] = []
    partial_reasons: list[str] = []
    page = 1

    while page <= max_pr_file_pages:
        payload = await github_fetch(
            f"/repos/{parsed_pr['owner']}/{parsed_pr['repo']}/pulls/{parsed_pr['pull_number']}/files?per_page=100&page={page}"
        )

        if not payload:
            break

        for item in payload:
            collected_files.append(
                ChangedFile(
                    filename=item["filename"],
                    status=item["status"],
                    additions=item["additions"],
                    deletions=item["deletions"],
                    changes=item["changes"],
                    patch=item.get("patch"),
                    blob_url=item.get("blob_url"),
                    previous_filename=item.get("previous_filename"),
                )
            )

        if len(payload) < 100:
            break

        page += 1

    if page > max_pr_file_pages:
        partial_reasons.append(
            f"GitHub file pagination was capped after {max_pr_file_pages * 100} files to protect service reliability."
        )

    if expected_file_count is not None and len(collected_files) < expected_file_count:
        partial_reasons.append(
            f"Reviewer analyzed {len(collected_files)} of {expected_file_count} changed files returned by GitHub."
        )

    return collected_files, partial_reasons


async def fetch_pr_commits(
    parsed_pr: dict[str, str | int],
    expected_commit_count: int | None = None,
) -> tuple[list[GithubCommitSummary], list[str]]:
    commits: list[GithubCommitSummary] = []
    partial_reasons: list[str] = []
    page = 1

    while page <= settings.max_pr_commit_pages:
        payload = await github_fetch(
            f"/repos/{parsed_pr['owner']}/{parsed_pr['repo']}/pulls/{parsed_pr['pull_number']}/commits?per_page=100&page={page}"
        )

        if not payload:
            break

        for item in payload:
            message = item.get("commit", {}).get("message", "")
            first_line = message.splitlines()[0] if message else "Commit"
            commits.append(
                GithubCommitSummary(
                    sha=item["sha"][:7],
                    message=first_line,
                    author=item.get("author", {}).get("login")
                    or item.get("commit", {}).get("author", {}).get("name")
                    or "unknown",
                    authored_at=item.get("commit", {}).get("author", {}).get("date"),
                    html_url=item.get("html_url"),
                )
            )

        if len(payload) < 100:
            break

        page += 1

    if page > settings.max_pr_commit_pages:
        partial_reasons.append(
            f"GitHub commit pagination was capped after {settings.max_pr_commit_pages * 100} commits to protect service reliability."
        )

    if expected_commit_count is not None and len(commits) < expected_commit_count:
        partial_reasons.append(
            f"Reviewer analyzed {len(commits)} of {expected_commit_count} commits returned by GitHub."
        )

    return commits, partial_reasons


async def fetch_repo_stars(owner: str, repo: str) -> int:
    payload = await github_fetch(f"/repos/{owner}/{repo}")
    return int(payload.get("stargazers_count", 0))
