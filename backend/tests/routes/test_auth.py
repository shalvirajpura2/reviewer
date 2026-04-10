from fastapi.testclient import TestClient

from app.main import app


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
