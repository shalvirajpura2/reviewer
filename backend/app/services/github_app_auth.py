import time

import jwt

from app.core.settings import settings
from app.services.github_client import github_fetch, github_send


def github_app_is_configured() -> bool:
    return bool(settings.github_app_id and settings.github_app_private_key)


def normalize_github_app_private_key(raw_value: str) -> str:
    return raw_value.strip().replace("\\n", "\n")


def build_github_app_jwt(now_timestamp: int | None = None) -> str:
    if not github_app_is_configured():
        raise PermissionError("Reviewer GitHub App auth is not configured. Set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY first.")

    issued_at = now_timestamp or int(time.time())
    payload = {
        "iat": issued_at - 60,
        "exp": issued_at + 540,
        "iss": settings.github_app_id,
    }
    private_key = normalize_github_app_private_key(settings.github_app_private_key)
    return jwt.encode(payload, private_key, algorithm="RS256")


async def fetch_repo_installation_id(parsed_pr: dict[str, str | int]) -> int:
    payload = await github_fetch(
        f"/repos/{parsed_pr['owner']}/{parsed_pr['repo']}/installation",
        github_token=build_github_app_jwt(),
    )

    installation_id = payload.get("id") if isinstance(payload, dict) else None
    if not installation_id:
        raise PermissionError("Reviewer GitHub App is not installed on this repository.")

    return int(installation_id)


async def fetch_installation_access_token(parsed_pr: dict[str, str | int]) -> str:
    installation_id = await fetch_repo_installation_id(parsed_pr)
    payload = await github_send(
        "POST",
        f"/app/installations/{installation_id}/access_tokens",
        {},
        "create the GitHub App installation token",
        github_token=build_github_app_jwt(),
    )

    installation_token = payload.get("token") if isinstance(payload, dict) else None
    if not installation_token:
        raise PermissionError("Reviewer GitHub App could not create an installation token for this repository.")

    return str(installation_token)
