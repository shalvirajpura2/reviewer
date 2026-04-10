import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from urllib.parse import urlencode

import httpx

from app.core.settings import settings
from app.models.auth import GithubAuthSession, GithubWebSessionStatus
from app.services.auth_session_service import default_scope, fetch_github_viewer
from app.services.json_file_store import read_json_object, write_json_object


github_authorize_url = "https://github.com/login/oauth/authorize"
github_access_token_url = "https://github.com/login/oauth/access_token"
github_session_cookie_name = "reviewer_web_session"
github_oauth_state_cookie_name = "reviewer_github_oauth_state"
github_oauth_next_cookie_name = "reviewer_github_oauth_next"
session_store_file = Path(__file__).resolve().parents[2] / "data" / "github_web_sessions.json"
session_store_lock = Lock()


def github_web_auth_is_configured() -> bool:
    return bool(settings.github_client_id and settings.github_client_secret)


def normalize_next_path(next_path: str | None) -> str:
    normalized = (next_path or "/github").strip()
    if not normalized.startswith("/"):
        return "/github"
    return normalized


def build_github_callback_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/api/auth/github/callback"


def build_github_authorize_redirect(base_url: str, state: str) -> str:
    if not github_web_auth_is_configured():
        raise PermissionError("Reviewer web GitHub auth is not configured. Set GITHUB_CLIENT_SECRET first.")

    query = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": build_github_callback_url(base_url),
            "scope": default_scope,
            "state": state,
        }
    )
    return f"{github_authorize_url}?{query}"


def resolve_frontend_redirect(next_path: str | None) -> str:
    return f"{settings.frontend_app_url}{normalize_next_path(next_path)}"


def build_web_session_status(session: GithubAuthSession | None) -> GithubWebSessionStatus:
    if session is None:
        return GithubWebSessionStatus(authenticated=False, configured=github_web_auth_is_configured())

    return GithubWebSessionStatus(
        authenticated=True,
        configured=github_web_auth_is_configured(),
        login=session.login,
        user_id=session.user_id,
    )


def create_oauth_state_token() -> str:
    return secrets.token_urlsafe(24)


def create_web_session_id() -> str:
    return secrets.token_urlsafe(32)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_session_timestamp(value: str) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def build_session_expiry() -> str:
    return (utc_now() + timedelta(seconds=settings.web_session_ttl_seconds)).isoformat()


def is_session_expired(session: GithubAuthSession) -> bool:
    expires_at = parse_session_timestamp(session.expires_at)
    if expires_at is None:
        return True
    return expires_at <= utc_now()


def load_session_store() -> dict[str, object]:
    return read_json_object(session_store_file, {"sessions": {}})


def save_session_store(payload: dict[str, object]) -> None:
    write_json_object(session_store_file, payload)


def prune_expired_sessions(payload: dict[str, object]) -> tuple[dict[str, object], bool]:
    sessions = payload.get("sessions", {})
    if not isinstance(sessions, dict):
        return {"sessions": {}}, True

    next_sessions: dict[str, object] = {}
    changed = False

    for session_id, session_payload in sessions.items():
        if not isinstance(session_payload, dict):
            changed = True
            continue

        try:
            session = GithubAuthSession(**session_payload)
        except Exception:
            changed = True
            continue

        if is_session_expired(session):
            changed = True
            continue

        next_sessions[session_id] = session.model_dump()

    return {"sessions": next_sessions}, changed


def load_web_auth_session(session_id: str | None) -> GithubAuthSession | None:
    if not session_id:
        return None

    with session_store_lock:
        payload, changed = prune_expired_sessions(load_session_store())
        if changed:
            save_session_store(payload)
        sessions = payload.get("sessions", {})
        if not isinstance(sessions, dict):
            return None

        session_payload = sessions.get(session_id, {})
        if not isinstance(session_payload, dict):
            return None

    try:
        session = GithubAuthSession(**session_payload)
    except Exception:
        return None

    if is_session_expired(session):
        clear_web_auth_session(session_id)
        return None

    return session


def require_web_auth_session(session_id: str | None) -> GithubAuthSession:
    session = load_web_auth_session(session_id)
    if session is None:
        raise PermissionError("GitHub login is required before using the GitHub bot dashboard.")
    return session


def save_web_auth_session(session: GithubAuthSession) -> str:
    session_id = create_web_session_id()
    session_payload = session.model_copy(
        update={
            "created_at": utc_now().isoformat(),
            "expires_at": build_session_expiry(),
        }
    )

    with session_store_lock:
        payload, changed = prune_expired_sessions(load_session_store())
        if changed:
            save_session_store(payload)
        sessions = payload.get("sessions", {})
        if not isinstance(sessions, dict):
            sessions = {}

        sessions[session_id] = session_payload.model_dump()
        payload["sessions"] = sessions
        save_session_store(payload)

    return session_id


def clear_web_auth_session(session_id: str | None) -> None:
    if not session_id:
        return

    with session_store_lock:
        payload = load_session_store()
        sessions = payload.get("sessions", {})
        if not isinstance(sessions, dict) or session_id not in sessions:
            return

        sessions.pop(session_id, None)
        payload["sessions"] = sessions
        save_session_store(payload)


async def exchange_github_oauth_code(code: str, base_url: str) -> GithubAuthSession:
    if not github_web_auth_is_configured():
        raise PermissionError("Reviewer web GitHub auth is not configured. Set GITHUB_CLIENT_SECRET first.")

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.post(
                github_access_token_url,
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": build_github_callback_url(base_url),
                },
            )
        except httpx.TimeoutException:
            raise ConnectionError("GitHub took too long to respond. Please try again.")
        except httpx.HTTPError:
            raise ConnectionError("GitHub could not be reached from the login service.")

    payload = response.json()
    access_token = str(payload.get("access_token") or "")
    if response.status_code >= 400 or not access_token:
        raise PermissionError("GitHub login could not be completed for the web dashboard.")

    viewer = await fetch_github_viewer(access_token)
    return GithubAuthSession(
        access_token=access_token,
        token_type=str(payload.get("token_type") or "bearer"),
        scope=str(payload.get("scope") or default_scope),
        login=viewer.login,
        user_id=viewer.user_id,
        source="web",
    )
