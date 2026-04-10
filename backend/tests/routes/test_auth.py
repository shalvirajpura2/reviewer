from fastapi.testclient import TestClient

from app.main import app
from app.routes import auth as auth_routes


client = TestClient(app)


def test_github_auth_start_route_sets_secure_cookies_for_https(monkeypatch):
    monkeypatch.setattr("app.routes.auth.create_oauth_state_token", lambda: "state-token")
    monkeypatch.setattr(
        "app.routes.auth.build_github_authorize_redirect",
        lambda base_url, state: f"{base_url}/authorize?state={state}",
    )

    response = client.get(
        "/api/auth/github/start",
        headers={
            "x-forwarded-proto": "https",
            "x-forwarded-host": "reviewer.live",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "Secure" in set_cookie_header
    assert "reviewer_github_oauth_state=state-token" in set_cookie_header


def test_github_auth_callback_sets_cross_site_session_cookie(monkeypatch):
    monkeypatch.setattr("app.routes.auth.save_web_auth_session", lambda session: "web-session-id")
    monkeypatch.setattr(auth_routes.settings, "frontend_app_url", "https://www.reviewer.live")

    async def fake_exchange_github_oauth_code(code: str, base_url: str):
        return fake_session()

    monkeypatch.setattr("app.routes.auth.exchange_github_oauth_code", fake_exchange_github_oauth_code)

    response = client.get(
        "/api/auth/github/callback?code=test-code&state=test-state",
        headers={
            "x-forwarded-proto": "https",
            "x-forwarded-host": "reviewer-production-79d1.up.railway.app",
        },
        cookies={
            "reviewer_github_oauth_state": "test-state",
            "reviewer_github_oauth_next": "/github",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "reviewer_web_session=web-session-id" in set_cookie_header
    assert "SameSite=none" in set_cookie_header
    assert "Secure" in set_cookie_header


def fake_session():
    from app.models.auth import GithubAuthSession

    return GithubAuthSession(
        access_token="web-token",
        token_type="bearer",
        scope="read:user public_repo",
        login="shalv",
        user_id=7,
        source="web",
    )
