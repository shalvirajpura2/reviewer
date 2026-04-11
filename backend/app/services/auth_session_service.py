import asyncio
import json
import os
import time
from pathlib import Path

import httpx

from app.core.settings import settings
from app.models.auth import GithubAuthSession, GithubDeviceCode, GithubViewer
from app.renderers.cli_ui import render_status
from app.services.github_client import clear_runtime_github_token, fetch_viewer, set_runtime_github_token


github_device_code_url = "https://github.com/login/device/code"
github_access_token_url = "https://github.com/login/oauth/access_token"
default_scope = "read:user public_repo"
session_file_name = "session.json"


def resolve_config_dir() -> Path:
    if settings.reviewer_config_dir:
        return Path(settings.reviewer_config_dir)

    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "reviewer-cli"
        return Path.home() / "AppData" / "Roaming" / "reviewer-cli"

    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "reviewer-cli"

    return Path.home() / ".config" / "reviewer-cli"


def resolve_session_path() -> Path:
    return resolve_config_dir() / session_file_name


def load_auth_session() -> GithubAuthSession | None:
    session_path = resolve_session_path()
    if not session_path.exists():
        return None

    try:
        payload = json.loads(session_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    try:
        return GithubAuthSession(**payload)
    except Exception:
        return None


def save_auth_session(session: GithubAuthSession) -> None:
    session_path = resolve_session_path()
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(session.model_dump_json(indent=2), encoding="utf-8")


def clear_auth_session() -> None:
    session_path = resolve_session_path()
    if session_path.exists():
        session_path.unlink()
    clear_runtime_github_token()


async def fetch_github_viewer(github_token: str) -> GithubViewer:
    payload = await fetch_viewer(github_token)
    login = str(payload.get("login") or "")
    user_id = int(payload.get("id") or 0)

    if not login or not user_id:
        raise PermissionError("GitHub authentication is invalid or expired. Please login again.")

    return GithubViewer(login=login, user_id=user_id)


async def start_device_login() -> GithubDeviceCode:
    if not settings.github_client_id:
        raise ValueError("GitHub device login is not configured. Set GITHUB_CLIENT_ID first.")

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.post(
                github_device_code_url,
                headers={"Accept": "application/json"},
                data={"client_id": settings.github_client_id, "scope": default_scope},
            )
        except httpx.TimeoutException:
            raise ConnectionError("GitHub took too long to respond. Please try again.")
        except httpx.HTTPError:
            raise ConnectionError("GitHub could not be reached from the login service.")

    if response.status_code >= 400:
        response_message = ""
        error_code = ""
        if response.content:
            try:
                payload = response.json()
            except ValueError:
                payload = None
            if isinstance(payload, dict):
                response_message = str(payload.get("error_description") or payload.get("message") or "").strip()
                error_code = str(payload.get("error") or "").strip()

        if error_code == "invalid_client":
            raise ValueError("GitHub device login could not be started because the client id is invalid.")

        if response.status_code in {429, 500, 502, 503, 504}:
            raise ConnectionError("GitHub device login is temporarily unavailable. Please try again.")

        if response_message:
            raise ValueError(f"GitHub device login could not be started: {response_message}")

        raise ValueError("GitHub device login could not be started.")

    payload = response.json()
    return GithubDeviceCode(**payload)


async def poll_for_access_token(device_code: GithubDeviceCode) -> GithubAuthSession:
    deadline = time.monotonic() + device_code.expires_in
    poll_interval = max(device_code.interval, 1)

    async with httpx.AsyncClient(timeout=20.0) as client:
        while time.monotonic() < deadline:
            await asyncio.sleep(poll_interval)

            try:
                response = await client.post(
                    github_access_token_url,
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": settings.github_client_id,
                        "device_code": device_code.device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                )
            except httpx.TimeoutException:
                raise ConnectionError("GitHub took too long to respond. Please try again.")
            except httpx.HTTPError:
                raise ConnectionError("GitHub could not be reached from the login service.")

            payload = response.json()
            error_code = str(payload.get("error") or "")

            if response.status_code < 400 and payload.get("access_token"):
                github_token = str(payload["access_token"])
                viewer = await fetch_github_viewer(github_token)
                return GithubAuthSession(
                    access_token=github_token,
                    token_type=str(payload.get("token_type") or "bearer"),
                    scope=str(payload.get("scope") or default_scope),
                    login=viewer.login,
                    user_id=viewer.user_id,
                    source="device",
                )

            if error_code == "authorization_pending":
                continue

            if error_code == "slow_down":
                poll_interval += 5
                continue

            if error_code == "access_denied":
                raise PermissionError("GitHub login was cancelled.")

            if error_code == "expired_token":
                raise PermissionError("GitHub login expired before authorization completed.")

            raise ValueError("GitHub login failed unexpectedly.")

    raise PermissionError("GitHub login expired before authorization completed.")


async def login_with_device_flow(print_fn=print) -> GithubAuthSession:
    device_code = await start_device_login()
    verification_target = device_code.verification_uri_complete or device_code.verification_uri

    print_fn("Reviewer GitHub Login")
    print_fn("=====================")
    print_fn("1. Open this link in your browser:")
    print_fn(f"   {verification_target}")
    print_fn("2. Enter this one-time code:")
    print_fn(f"   {device_code.user_code}")
    print_fn("3. Approve Reviewer CLI in GitHub")
    print_fn(render_status("wait", "Waiting for GitHub approval..."))

    session = await poll_for_access_token(device_code)
    save_auth_session(session)
    set_runtime_github_token(session.access_token)
    print_fn(render_status("ok", f"Signed in as @{session.login}. You can run review commands now."))
    return session


async def resolve_authenticated_session(auto_login: bool = False, print_fn=print) -> GithubAuthSession | None:
    saved_session = load_auth_session()
    if saved_session:
        try:
            viewer = await fetch_github_viewer(saved_session.access_token)
        except PermissionError:
            clear_auth_session()
            print_fn(render_status("info", "Saved GitHub session expired. Starting a fresh login."))
        else:
            normalized_session = GithubAuthSession(
                access_token=saved_session.access_token,
                token_type=saved_session.token_type,
                scope=saved_session.scope,
                login=viewer.login,
                user_id=viewer.user_id,
                source="device",
            )
            save_auth_session(normalized_session)
            set_runtime_github_token(normalized_session.access_token)
            return normalized_session

    if settings.github_token:
        viewer = await fetch_github_viewer(settings.github_token)
        set_runtime_github_token(settings.github_token)
        return GithubAuthSession(
            access_token=settings.github_token,
            token_type="bearer",
            scope=default_scope,
            login=viewer.login,
            user_id=viewer.user_id,
            source="env",
        )

    if auto_login:
        print_fn(render_status("info", "No active GitHub session found. Starting login so we can continue."))
        return await login_with_device_flow(print_fn=print_fn)

    return None


async def require_authenticated_session(print_fn=print) -> GithubAuthSession:
    session = await resolve_authenticated_session(auto_login=True, print_fn=print_fn)
    if session is None:
        raise PermissionError("GitHub login is required before running this command.")
    return session


async def whoami_session() -> GithubAuthSession | None:
    return await resolve_authenticated_session(auto_login=False)


def logout_session() -> bool:
    had_session = load_auth_session() is not None
    clear_auth_session()
    return had_session
