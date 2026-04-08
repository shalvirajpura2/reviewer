from fastapi.testclient import TestClient

from app.main import app
from app.models.github_bot import GithubBotPullRequestsResponse, GithubBotRepositoriesResponse, GithubBotRepositorySettings, GithubBotRepositorySummary, GithubBotPullRequestSummary

client = TestClient(app)


def test_list_connected_repositories_route(monkeypatch):
    async def fake_list_connected_repositories():
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
                )
            ]
        )

    monkeypatch.setattr("app.routes.github_bot.list_connected_repositories", fake_list_connected_repositories)

    response = client.get("/api/github-bot/repositories", headers={"x-request-id": "req-bot-repos"})

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "req-bot-repos"
    assert response.json()["repositories"][0]["full_name"] == "acme/reviewer"


def test_list_repository_pull_requests_route(monkeypatch):
    async def fake_list_repository_pull_requests(owner: str, repo: str):
        assert owner == "acme"
        assert repo == "reviewer"
        return GithubBotPullRequestsResponse(
            repository=GithubBotRepositorySummary(
                owner="acme",
                repo="reviewer",
                full_name="acme/reviewer",
                installation_id=12,
                default_branch="main",
                open_pull_requests=1,
                settings=GithubBotRepositorySettings(manual_review=True, automatic_review=False, review_new_pushes=False),
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

    response = client.get("/api/github-bot/repositories/acme/reviewer/pulls")

    assert response.status_code == 200
    assert response.json()["pull_requests"][0]["number"] == 18


def test_repository_settings_routes(monkeypatch):
    monkeypatch.setattr(
        "app.routes.github_bot.get_repository_settings",
        lambda owner, repo: GithubBotRepositorySettings(manual_review=True, automatic_review=False, review_new_pushes=False),
    )

    def fake_update_repository_settings(owner: str, repo: str, settings: GithubBotRepositorySettings):
        assert owner == "acme"
        assert repo == "reviewer"
        return settings

    monkeypatch.setattr("app.routes.github_bot.update_repository_settings", fake_update_repository_settings)

    get_response = client.get("/api/github-bot/repositories/acme/reviewer/settings")
    put_response = client.put(
        "/api/github-bot/repositories/acme/reviewer/settings",
        json={"manual_review": True, "automatic_review": True, "review_new_pushes": True},
    )

    assert get_response.status_code == 200
    assert put_response.status_code == 200
    assert put_response.json()["automatic_review"] is True
