import asyncio
from typing import Any

import httpx

from app.core.settings import settings
from app.models.analysis import ChangedFile, CheckRunSummary, GithubCommitSummary, GithubPrMetadata

max_pr_file_pages = 30
github_retry_attempts = 3
github_retry_backoff_seconds = 0.35
github_client: httpx.AsyncClient | None = None
github_client_lock = asyncio.Lock()


def build_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "reviewer-v1",
    }

    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    return headers


async def get_github_client() -> httpx.AsyncClient:
    global github_client

    if github_client and not github_client.is_closed:
        return github_client

    async with github_client_lock:
        if github_client and not github_client.is_closed:
            return github_client

        github_client = httpx.AsyncClient(timeout=20.0)
        return github_client


async def close_github_client() -> None:
    global github_client

    if not github_client or github_client.is_closed:
        return

    async with github_client_lock:
        if github_client and not github_client.is_closed:
            await github_client.aclose()
        github_client = None


async def github_fetch(path: str) -> Any:
    last_error: Exception | None = None

    for attempt_number in range(1, github_retry_attempts + 1):
        try:
            client = await get_github_client()
            response = await client.get(f"{settings.github_api_base}{path}", headers=build_headers())
        except httpx.TimeoutException as error:
            last_error = ConnectionError("GitHub took too long to respond. Please try again.")
        except httpx.HTTPError:
            last_error = ConnectionError("GitHub could not be reached from the analysis service.")
        else:
            if response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0":
                raise PermissionError("GitHub rate limit reached. Add a GITHUB_TOKEN or try again later.")

            if response.status_code == 403 and "secondary rate limit" in response.text.lower():
                raise PermissionError("GitHub temporarily rate limited this analysis. Please retry shortly.")

            if response.status_code == 404:
                raise FileNotFoundError("Repository or pull request not found, or the PR is not public.")

            if response.status_code in {502, 503, 504}:
                last_error = ConnectionError("GitHub is temporarily unavailable. Please try again.")
            elif response.status_code >= 400:
                raise ValueError("GitHub returned an unexpected response while fetching the pull request.")
            else:
                return response.json()

        if attempt_number < github_retry_attempts:
            await asyncio.sleep(github_retry_backoff_seconds * attempt_number)

    if last_error:
        raise last_error

    raise ConnectionError("GitHub could not be reached from the analysis service.")


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
        state=payload.get("state", ""),
        merged=bool(payload.get("merged", False)),
        merged_at=payload.get("merged_at"),
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


async def fetch_commit_check_runs(parsed_pr: dict[str, str | int], head_sha: str) -> tuple[list[CheckRunSummary], list[str]]:
    if not head_sha:
        return [], ["GitHub did not return a PR head SHA, so CI check status could not be verified."]

    try:
        payload = await github_fetch(
            f"/repos/{parsed_pr['owner']}/{parsed_pr['repo']}/commits/{head_sha}/check-runs?per_page=100"
        )
    except FileNotFoundError:
        return [], ["GitHub did not expose check runs for this commit, so CI status could not be verified."]

    if not isinstance(payload, dict):
        return [], ["GitHub returned an unexpected check-run payload, so CI status could not be verified."]

    raw_check_runs = payload.get("check_runs", [])
    if not isinstance(raw_check_runs, list):
        return [], ["GitHub returned an unexpected check-run payload, so CI status could not be verified."]

    check_runs = [
        CheckRunSummary(
            name=str(item.get("name") or "Unnamed check"),
            status=str(item.get("status") or "unknown"),
            conclusion=item.get("conclusion"),
            details_url=item.get("details_url") or item.get("html_url"),
        )
        for item in raw_check_runs[:50]
        if isinstance(item, dict)
    ]

    total_count = int(payload.get("total_count", len(check_runs)) or len(check_runs))
    partial_reasons = []
    if total_count > len(check_runs):
        partial_reasons.append(
            f"Reviewer loaded {len(check_runs)} of {total_count} check runs returned by GitHub."
        )

    return check_runs, partial_reasons


async def fetch_repo_stars(owner: str, repo: str) -> int:
    payload = await github_fetch(f"/repos/{owner}/{repo}")
    return int(payload.get("stargazers_count", 0))