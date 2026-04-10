from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

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


def resolve_public_base_url(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").strip()
    forwarded_host = request.headers.get("x-forwarded-host", "").strip()
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    return str(request.base_url).rstrip("/")


def use_secure_cookies(request: Request) -> bool:
    return resolve_public_base_url(request).startswith("https://")


@router.get("/session", response_model=GithubWebSessionStatus)
async def github_session_route(request: Request):
    session = load_web_auth_session(request.cookies.get(github_session_cookie_name))
    return build_web_session_status(session)


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
        redirect_response.set_cookie(github_session_cookie_name, session_id, httponly=True, samesite="lax", secure=use_secure_cookies(request), path="/")
        redirect_response.delete_cookie(github_oauth_state_cookie_name, path="/")
        redirect_response.delete_cookie(github_oauth_next_cookie_name, path="/")
        return redirect_response
    except PermissionError as error:
        return error_response(request, 403, "forbidden", str(error))
    except ConnectionError as error:
        return error_response(request, 503, "upstream_unavailable", str(error))


@router.post("/logout")
async def github_logout_route(request: Request):
    clear_web_auth_session(request.cookies.get(github_session_cookie_name))
    response = JSONResponse({"ok": True})
    response.delete_cookie(github_session_cookie_name, path="/")
    response.delete_cookie(github_oauth_state_cookie_name, path="/")
    response.delete_cookie(github_oauth_next_cookie_name, path="/")
    return response
