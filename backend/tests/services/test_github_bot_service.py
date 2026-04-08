import pytest

from app.models.github_bot import GithubBotRepositorySettings
from app.services import github_bot_service


@pytest.mark.asyncio
async def test_list_connected_repositories_merges_installations_and_settings(monkeypatch):
    async def fake_fetch_app_installations():
        return [{"id": 12}]

    async def fake_fetch_installation_repositories(installation_id: int):
        assert installation_id == 12
        return [
            {
                "name": "reviewer",
                "full_name": "acme/reviewer",
                "default_branch": "main",
                "owner": {"login": "acme"},
            }
        ]

    async def fake_fetch_installation_access_token_by_id(installation_id: int):
        assert installation_id == 12
        return "installation-token"

    async def fake_fetch_open_pull_requests(owner: str, repo: str, github_token=None):
        assert owner == "acme"
        assert repo == "reviewer"
        assert github_token == "installation-token"
        return [{"number": 9}, {"number": 10}]

    monkeypatch.setattr(github_bot_service, "github_app_is_configured", lambda: True)
    monkeypatch.setattr(github_bot_service, "fetch_app_installations", fake_fetch_app_installations)
    monkeypatch.setattr(github_bot_service, "fetch_installation_repositories", fake_fetch_installation_repositories)
    monkeypatch.setattr(github_bot_service, "fetch_installation_access_token_by_id", fake_fetch_installation_access_token_by_id)
    monkeypatch.setattr(github_bot_service, "fetch_open_pull_requests", fake_fetch_open_pull_requests)
    monkeypatch.setattr(github_bot_service, "load_repository_settings", lambda owner, repo: GithubBotRepositorySettings(manual_review=True, automatic_review=True, review_new_pushes=False))

    result = await github_bot_service.list_connected_repositories()

    assert len(result.repositories) == 1
    assert result.repositories[0].full_name == "acme/reviewer"
    assert result.repositories[0].open_pull_requests == 2
    assert result.repositories[0].settings.automatic_review is True


@pytest.mark.asyncio
async def test_list_repository_pull_requests_maps_mode_from_settings(monkeypatch):
    async def fake_fetch_repo_installation_id(parsed_pr):
        assert parsed_pr["owner"] == "acme"
        assert parsed_pr["repo"] == "reviewer"
        return 12

    async def fake_fetch_installation_access_token_by_id(installation_id: int):
        assert installation_id == 12
        return "installation-token"

    async def fake_fetch_open_pull_requests(owner: str, repo: str, github_token=None):
        assert github_token == "installation-token"
        return [
            {
                "number": 14,
                "title": "Ship the bot API",
                "user": {"login": "shalv"},
                "updated_at": "2026-04-08T10:00:00Z",
                "html_url": "https://github.com/acme/reviewer/pull/14",
                "base": {"ref": "main"},
                "head": {"ref": "feat/bot-api"},
                "draft": False,
            }
        ]

    monkeypatch.setattr(github_bot_service, "fetch_repo_installation_id", fake_fetch_repo_installation_id)
    monkeypatch.setattr(github_bot_service, "fetch_installation_access_token_by_id", fake_fetch_installation_access_token_by_id)
    monkeypatch.setattr(github_bot_service, "fetch_open_pull_requests", fake_fetch_open_pull_requests)
    monkeypatch.setattr(github_bot_service, "load_repository_settings", lambda owner, repo: GithubBotRepositorySettings(manual_review=True, automatic_review=True, review_new_pushes=True))

    result = await github_bot_service.list_repository_pull_requests("acme", "reviewer")

    assert result.repository.full_name == "acme/reviewer"
    assert result.pull_requests[0].number == 14
    assert result.pull_requests[0].mode == "review_new_pushes"


def test_update_repository_settings_delegates_to_store(monkeypatch):
    captured = {}

    def fake_save_repository_settings(owner: str, repo: str, settings: GithubBotRepositorySettings):
        captured["owner"] = owner
        captured["repo"] = repo
        captured["settings"] = settings
        return settings

    monkeypatch.setattr(github_bot_service, "save_repository_settings", fake_save_repository_settings)

    settings = github_bot_service.update_repository_settings(
        "acme",
        "reviewer",
        GithubBotRepositorySettings(manual_review=True, automatic_review=False, review_new_pushes=False),
    )

    assert captured["owner"] == "acme"
    assert captured["repo"] == "reviewer"
    assert settings.manual_review is True



@pytest.mark.asyncio
async def test_trigger_manual_review_reuses_publish_summary(monkeypatch):
    captured = {}

    async def fake_publish_review_summary(pr_url: str, client_key: str, use_backend_publish_token: bool = False):
        captured["pr_url"] = pr_url
        captured["client_key"] = client_key
        captured["use_backend_publish_token"] = use_backend_publish_token
        return {"ok": True}

    monkeypatch.setattr(github_bot_service, "publish_review_summary", fake_publish_review_summary)

    result = await github_bot_service.trigger_manual_review("acme", "reviewer", 18, "testclient")

    assert result == {"ok": True}
    assert captured["pr_url"] == "https://github.com/acme/reviewer/pull/18"
    assert captured["client_key"] == "testclient"
    assert captured["use_backend_publish_token"] is True

