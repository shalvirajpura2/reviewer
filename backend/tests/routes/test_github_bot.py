import json

from fastapi.testclient import TestClient

from app.main import app
from app.models.auth import GithubAuthSession
from app.models.github_bot import (
    GithubBotPullRequestsResponse,
    GithubBotRepositoriesResponse,
    GithubBotRepositoryActivity,
    GithubBotRepositorySettings,
    GithubBotRepositorySummary,
    GithubBotPullRequestSummary,
)

client = TestClient(app)


def csrf_headers() -> dict[str, str]:
    return {"x-reviewer-csrf": "csrf-token"}


def fake_web_session() -> GithubAuthSession:
    return GithubAuthSession(
        access_token="web-token",
        token_type="bearer",
        scope="read:user public_repo",
        login="shalv",
        user_id=7,
        source="web",
    )


def test_list_connected_repositories_route(monkeypatch):
    async def fake_list_connected_repositories(github_token: str):
        assert github_token == "web-token"
        return GithubBotRepositoriesResponse(
            repositories=[
                GithubBotRepositorySummary(
                    owner="acme",
                    repo="reviewer",
                    full_name="acme/reviewer",
                    installation_id=12,
                    default_branch="main",
                    open_pull_requests=2,
                    settings=GithubBotRepositorySettings(manual_review=True, automatic_review=True, review_new_pushes=False),
                    activity=GithubBotRepositoryActivity(last_review_at="", last_pull_number=0, last_trigger="", last_action="", last_comment_url=None),
                )
            ]
        )

    monkeypatch.setattr("app.routes.github_bot.list_connected_repositories", fake_list_connected_repositories)
    monkeypatch.setattr("app.routes.github_bot.require_web_auth_session", lambda session_id: fake_web_session())

    response = client.get("/api/github-bot/repositories", headers={"x-request-id": "req-bot-repos"})

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "req-bot-repos"
    assert response.json()["repositories"][0]["full_name"] == "acme/reviewer"


def test_list_repository_pull_requests_route(monkeypatch):
    async def fake_list_repository_pull_requests(owner: str, repo: str, github_token: str):
        assert owner == "acme"
        assert repo == "reviewer"
        assert github_token == "web-token"
        return GithubBotPullRequestsResponse(
            repository=GithubBotRepositorySummary(
                owner="acme",
                repo="reviewer",
                full_name="acme/reviewer",
                installation_id=12,
                default_branch="main",
                open_pull_requests=1,
                settings=GithubBotRepositorySettings(manual_review=True, automatic_review=False, review_new_pushes=False),
                activity=GithubBotRepositoryActivity(last_review_at="", last_pull_number=0, last_trigger="", last_action="", last_comment_url=None),
            ),
            pull_requests=[
                GithubBotPullRequestSummary(
                    number=18,
                    title="Ship bot publishing",
                    author="shalv",
                    updated_at="2026-04-08T10:00:00Z",
                    html_url="https://github.com/acme/reviewer/pull/18",
                    base_branch="main",
                    head_branch="feat/bot",
                    draft=False,
                    mode="manual_review",
                )
            ],
        )

    monkeypatch.setattr("app.routes.github_bot.list_repository_pull_requests", fake_list_repository_pull_requests)
    monkeypatch.setattr("app.routes.github_bot.require_web_auth_session", lambda session_id: fake_web_session())

    response = client.get("/api/github-bot/repositories/acme/reviewer/pulls")

    assert response.status_code == 200
    assert response.json()["pull_requests"][0]["number"] == 18


def test_repository_settings_routes(monkeypatch):
    monkeypatch.setattr("app.routes.github_bot.require_web_auth_session", lambda session_id: fake_web_session())
    client.cookies.set("reviewer_web_csrf", "csrf-token")

    async def fake_get_repository_settings(owner: str, repo: str, github_token: str):
        assert github_token == "web-token"
        return GithubBotRepositorySettings(manual_review=True, automatic_review=False, review_new_pushes=False)

    monkeypatch.setattr("app.routes.github_bot.get_repository_settings", fake_get_repository_settings)

    async def fake_update_repository_settings(owner: str, repo: str, settings: GithubBotRepositorySettings, github_token: str):
        assert owner == "acme"
        assert repo == "reviewer"
        assert github_token == "web-token"
        return settings

    monkeypatch.setattr("app.routes.github_bot.update_repository_settings", fake_update_repository_settings)

    get_response = client.get("/api/github-bot/repositories/acme/reviewer/settings")
    put_response = client.put(
        "/api/github-bot/repositories/acme/reviewer/settings",
        json={"manual_review": True, "automatic_review": True, "review_new_pushes": True},
        headers=csrf_headers(),
    )

    assert get_response.status_code == 200
    assert put_response.status_code == 200
    assert put_response.json()["automatic_review"] is True


def test_trigger_manual_review_route(monkeypatch):
    from app.models.review_domain import ReviewCommentPublication

    async def fake_trigger_manual_review(owner: str, repo: str, pull_number: int, client_key: str, github_token: str):
        assert owner == "acme"
        assert repo == "reviewer"
        assert pull_number == 18
        assert client_key == "testclient"
        assert github_token == "web-token"
        return ReviewCommentPublication(
            action="created",
            comment_id=501,
            html_url="https://github.com/acme/reviewer/pull/18#issuecomment-501",
            body="comment body",
        )

    monkeypatch.setattr("app.routes.github_bot.trigger_manual_review", fake_trigger_manual_review)
    monkeypatch.setattr("app.routes.github_bot.require_web_auth_session", lambda session_id: fake_web_session())
    client.cookies.set("reviewer_web_csrf", "csrf-token")

    response = client.post(
        "/api/github-bot/repositories/acme/reviewer/review",
        json={"pull_number": 18},
        headers={"x-request-id": "req-bot-review", **csrf_headers()},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "req-bot-review"
    assert response.json()["comment_id"] == 501


def test_github_webhook_route(monkeypatch):
    async def fake_handle_github_webhook(payload: bytes, event_name: str, signature_header: str, delivery_id: str = ""):
        assert json.loads(payload.decode("utf-8"))["action"] == "opened"
        assert event_name == "pull_request"
        assert signature_header == "sha256=test"
        assert delivery_id == "delivery-1"
        return {
            "status": "processed",
            "event": "pull_request",
            "action": "opened",
            "detail": "Reviewer posted an automated GitHub summary for acme/reviewer#18.",
        }

    monkeypatch.setattr("app.routes.github_bot.handle_github_webhook", fake_handle_github_webhook)

    response = client.post(
        "/api/github-bot/webhooks/github",
        content=b'{"action":"opened"}',
        headers={
            "x-request-id": "req-bot-webhook",
            "x-github-event": "pull_request",
            "x-hub-signature-256": "sha256=test",
            "x-github-delivery": "delivery-1",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "req-bot-webhook"
    assert response.json()["status"] == "processed"


def test_github_webhook_route_maps_signature_errors(monkeypatch):
    async def fake_handle_github_webhook(payload: bytes, event_name: str, signature_header: str, delivery_id: str = ""):
        raise PermissionError("GitHub webhook signature is invalid.")

    monkeypatch.setattr("app.routes.github_bot.handle_github_webhook", fake_handle_github_webhook)

    response = client.post(
        "/api/github-bot/webhooks/github",
        content=b'{}',
        headers={
            "x-github-event": "pull_request",
            "x-hub-signature-256": "sha256=test",
        },
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "forbidden"
