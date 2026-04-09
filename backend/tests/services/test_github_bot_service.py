import pytest

from app.models.github_bot import GithubBotRepositoryActivity, GithubBotRepositorySettings
from app.models.review_domain import ReviewCommentPublication
from app.services import github_bot_service


@pytest.mark.asyncio
async def test_list_connected_repositories_merges_installations_settings_and_activity(monkeypatch):
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
    monkeypatch.setattr(github_bot_service, "load_repository_activity", lambda owner, repo: GithubBotRepositoryActivity(last_review_at="2026-04-09T10:00:00+00:00", last_pull_number=10, last_trigger="manual_review", last_action="created", last_comment_url="https://github.com/acme/reviewer/pull/10#issuecomment-1"))

    result = await github_bot_service.list_connected_repositories()

    assert len(result.repositories) == 1
    assert result.repositories[0].full_name == "acme/reviewer"
    assert result.repositories[0].open_pull_requests == 2
    assert result.repositories[0].settings.automatic_review is True
    assert result.repositories[0].activity.last_pull_number == 10


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
    monkeypatch.setattr(github_bot_service, "load_repository_activity", lambda owner, repo: GithubBotRepositoryActivity(last_review_at="", last_pull_number=0, last_trigger="", last_action="", last_comment_url=None))

    result = await github_bot_service.list_repository_pull_requests("acme", "reviewer")

    assert result.repository.full_name == "acme/reviewer"
    assert result.pull_requests[0].number == 14
    assert result.pull_requests[0].mode == "review_new_pushes"
    assert result.repository.activity.last_pull_number == 0


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
async def test_trigger_manual_review_records_repository_activity(monkeypatch):
    captured = {}

    async def fake_publish_review_summary(pr_url: str, client_key: str, use_backend_publish_token: bool = False):
        captured["pr_url"] = pr_url
        captured["client_key"] = client_key
        captured["use_backend_publish_token"] = use_backend_publish_token
        return ReviewCommentPublication(
            action="created",
            comment_id=501,
            html_url="https://github.com/acme/reviewer/pull/18#issuecomment-501",
            body="comment body",
        )

    def fake_record_repository_activity(owner: str, repo: str, pull_number: int, trigger_source: str, publication: ReviewCommentPublication):
        captured["activity_owner"] = owner
        captured["activity_repo"] = repo
        captured["activity_pull_number"] = pull_number
        captured["activity_trigger_source"] = trigger_source
        captured["activity_comment_id"] = publication.comment_id

    monkeypatch.setattr(github_bot_service, "publish_review_summary", fake_publish_review_summary)
    monkeypatch.setattr(github_bot_service, "record_repository_activity", fake_record_repository_activity)

    result = await github_bot_service.trigger_manual_review("acme", "reviewer", 18, "testclient")

    assert result.comment_id == 501
    assert captured["pr_url"] == "https://github.com/acme/reviewer/pull/18"
    assert captured["client_key"] == "testclient"
    assert captured["use_backend_publish_token"] is True
    assert captured["activity_owner"] == "acme"
    assert captured["activity_repo"] == "reviewer"
    assert captured["activity_pull_number"] == 18
    assert captured["activity_trigger_source"] == "manual_review"
    assert captured["activity_comment_id"] == 501