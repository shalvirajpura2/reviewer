from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from urllib.parse import urlencode, urlparse
import hmac

from app.core.settings import settings
from app.models.auth import GithubWebSessionStatus
from app.routes.analyze import error_response
from app.services.web_auth_session_service import (
    build_github_authorize_redirect,
    build_web_session_status,
    clear_web_auth_session,
    exchange_github_oauth_code,
    github_oauth_next_cookie_name,
    github_oauth_state_cookie_name,
    github_session_cookie_name,
    load_web_auth_session,
    normalize_next_path,
    resolve_frontend_redirect,
    save_web_auth_session,
    create_oauth_state_token,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])
github_csrf_cookie_name = "reviewer_web_csrf"
github_csrf_header_name = "x-reviewer-csrf"


def resolve_public_base_url(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").strip()
    forwarded_host = request.headers.get("x-forwarded-host", "").strip()
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    return str(request.base_url).rstrip("/")


def use_secure_cookies(request: Request) -> bool:
    return resolve_public_base_url(request).startswith("https://")


def session_cookie_samesite(request: Request) -> str:
    backend_host = urlparse(resolve_public_base_url(request)).hostname or ""
    frontend_host = urlparse(settings.frontend_app_url).hostname or ""
    if backend_host and frontend_host and backend_host != frontend_host:
        return "none"
    return "lax"


def allowed_request_origins(request: Request) -> set[str]:
    origins = {settings.frontend_app_url.rstrip("/")}
    origins.update(origin.rstrip("/") for origin in settings.cors_allow_origins if origin)
    origins.add(resolve_public_base_url(request).rstrip("/"))
    return {origin for origin in origins if origin}


def request_origin(request: Request) -> str:
    header_origin = request.headers.get("origin", "").strip()
    if header_origin:
        return header_origin.rstrip("/")

    referer = request.headers.get("referer", "").strip()
    if not referer:
        return ""

    parsed_referer = urlparse(referer)
    if not parsed_referer.scheme or not parsed_referer.netloc:
        return ""

    return f"{parsed_referer.scheme}://{parsed_referer.netloc}".rstrip("/")


def require_web_csrf(request: Request) -> None:
    source_origin = request_origin(request)
    if source_origin and source_origin not in allowed_request_origins(request):
        raise PermissionError("The request origin is not allowed for this session.")

    csrf_cookie = request.cookies.get(github_csrf_cookie_name, "").strip()
    csrf_header = request.headers.get(github_csrf_header_name, "").strip()

    if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise PermissionError("CSRF validation failed. Refresh the page and try again.")


def resolve_install_next_path(state: str) -> str:
    if not state:
        return "/github"

    parsed_state = urlparse(state)
    if parsed_state.scheme or parsed_state.netloc:
        frontend_host = urlparse(settings.frontend_app_url).hostname or ""
        if parsed_state.hostname and frontend_host and parsed_state.hostname == frontend_host:
            candidate = parsed_state.path or "/github"
            if parsed_state.query:
                candidate = f"{candidate}?{parsed_state.query}"
            return normalize_next_path(candidate)
        return "/github"

    return normalize_next_path(state)


@router.get("/session", response_model=GithubWebSessionStatus)
async def github_session_route(request: Request):
    session = load_web_auth_session(request.cookies.get(github_session_cookie_name))
    return build_web_session_status(session).model_copy(update={"csrf_token": request.cookies.get(github_csrf_cookie_name, "")})


@router.get("/github/start")
async def github_auth_start_route(request: Request, next: str = "/github"):
    try:
        state = create_oauth_state_token()
        response = RedirectResponse(build_github_authorize_redirect(resolve_public_base_url(request), state), status_code=302)
        response.set_cookie(github_oauth_state_cookie_name, state, httponly=True, samesite="lax", secure=use_secure_cookies(request), path="/")
        response.set_cookie(github_oauth_next_cookie_name, normalize_next_path(next), httponly=True, samesite="lax", secure=use_secure_cookies(request), path="/")
        return response
    except PermissionError as error:
        return error_response(request, 403, "forbidden", str(error))


@router.get("/github/callback")
async def github_auth_callback_route(request: Request, code: str = "", state: str = ""):
    try:
        expected_state = request.cookies.get(github_oauth_state_cookie_name, "")
        if not code or not state or not expected_state or state != expected_state:
            raise PermissionError("GitHub login state is invalid. Please try connecting GitHub again.")

        session = await exchange_github_oauth_code(code, resolve_public_base_url(request))
        session_id = save_web_auth_session(session)
        redirect_response = RedirectResponse(
            resolve_frontend_redirect(request.cookies.get(github_oauth_next_cookie_name)),
            status_code=302,
        )
        redirect_response.set_cookie(
            github_session_cookie_name,
            session_id,
            httponly=True,
            samesite=session_cookie_samesite(request),
            secure=use_secure_cookies(request),
            path="/",
        )
        redirect_response.set_cookie(
            github_csrf_cookie_name,
            create_oauth_state_token(),
            httponly=False,
            samesite=session_cookie_samesite(request),
            secure=use_secure_cookies(request),
            path="/",
        )
        redirect_response.delete_cookie(github_oauth_state_cookie_name, path="/")
        redirect_response.delete_cookie(github_oauth_next_cookie_name, path="/")
        return redirect_response
    except PermissionError as error:
        return error_response(request, 403, "forbidden", str(error))
    except ConnectionError as error:
        return error_response(request, 503, "upstream_unavailable", str(error))


@router.post("/logout")
async def github_logout_route(request: Request):
    require_web_csrf(request)
    clear_web_auth_session(request.cookies.get(github_session_cookie_name))
    response = JSONResponse({"ok": True})
    response.delete_cookie(github_session_cookie_name, path="/")
    response.delete_cookie(github_csrf_cookie_name, path="/")
    response.delete_cookie(github_oauth_state_cookie_name, path="/")
    response.delete_cookie(github_oauth_next_cookie_name, path="/")
    return response


@router.get("/github/app-install/callback")
async def github_app_install_callback_route(
    request: Request,
    installation_id: str = "",
    setup_action: str = "",
    state: str = "",
):
    next_path = resolve_install_next_path(state)
    redirect_target = resolve_frontend_redirect(next_path)
    query_pairs: list[tuple[str, str]] = []

    if setup_action:
        query_pairs.append(("setup_action", setup_action))

    if installation_id:
        query_pairs.append(("installation_id", installation_id))

    if query_pairs:
        separator = "&" if "?" in redirect_target else "?"
        redirect_target = f"{redirect_target}{separator}{urlencode(query_pairs)}"

    return RedirectResponse(redirect_target, status_code=302)
