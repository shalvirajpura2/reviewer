import pytest

from app.models.github_bot import GithubBotRepositorySettings
from app.services import github_webhook_service


@pytest.mark.asyncio
async def test_handle_github_webhook_processes_opened_pull_request(monkeypatch):
    monkeypatch.setattr(github_webhook_service.settings, "github_webhook_secret", "secret")

    async def fake_trigger_manual_review(owner: str, repo: str, pull_number: int, client_key: str):
        assert owner == "acme"
        assert repo == "reviewer"
        assert pull_number == 18
        assert client_key == "github_webhook:delivery-1"
        return {"ok": True}

    monkeypatch.setattr(github_webhook_service, "trigger_manual_review", fake_trigger_manual_review)
    monkeypatch.setattr(
        github_webhook_service,
        "load_repository_settings",
        lambda owner, repo: GithubBotRepositorySettings(manual_review=True, automatic_review=True, review_new_pushes=False),
    )

    payload = b'{"action":"opened","repository":{"name":"reviewer","owner":{"login":"acme"}},"pull_request":{"number":18,"state":"open"}}'
    signature = github_webhook_service.build_github_webhook_signature(payload, "secret")

    result = await github_webhook_service.handle_github_webhook(payload, "pull_request", signature, "delivery-1")

    assert result.status == "processed"
    assert result.action == "opened"


@pytest.mark.asyncio
async def test_handle_github_webhook_processes_synchronize_when_enabled(monkeypatch):
    monkeypatch.setattr(github_webhook_service.settings, "github_webhook_secret", "secret")
    monkeypatch.setattr(
        github_webhook_service,
        "load_repository_settings",
        lambda owner, repo: GithubBotRepositorySettings(manual_review=True, automatic_review=False, review_new_pushes=True),
    )

    async def fake_trigger_manual_review(owner: str, repo: str, pull_number: int, client_key: str):
        return {"ok": True}

    monkeypatch.setattr(github_webhook_service, "trigger_manual_review", fake_trigger_manual_review)

    payload = b'{"action":"synchronize","repository":{"name":"reviewer","owner":{"login":"acme"}},"pull_request":{"number":21,"state":"open"}}'
    signature = github_webhook_service.build_github_webhook_signature(payload, "secret")

    result = await github_webhook_service.handle_github_webhook(payload, "pull_request", signature, "delivery-2")

    assert result.status == "processed"
    assert result.action == "synchronize"


@pytest.mark.asyncio
async def test_handle_github_webhook_ignores_event_when_settings_do_not_match(monkeypatch):
    monkeypatch.setattr(github_webhook_service.settings, "github_webhook_secret", "secret")
    monkeypatch.setattr(
        github_webhook_service,
        "load_repository_settings",
        lambda owner, repo: GithubBotRepositorySettings(manual_review=True, automatic_review=False, review_new_pushes=False),
    )

    async def fake_trigger_manual_review(owner: str, repo: str, pull_number: int, client_key: str):
        raise AssertionError("trigger_manual_review should not be called")

    monkeypatch.setattr(github_webhook_service, "trigger_manual_review", fake_trigger_manual_review)

    payload = b'{"action":"opened","repository":{"name":"reviewer","owner":{"login":"acme"}},"pull_request":{"number":18,"state":"open"}}'
    signature = github_webhook_service.build_github_webhook_signature(payload, "secret")

    result = await github_webhook_service.handle_github_webhook(payload, "pull_request", signature)

    assert result.status == "ignored"


@pytest.mark.asyncio
async def test_handle_github_webhook_accepts_ping(monkeypatch):
    monkeypatch.setattr(github_webhook_service.settings, "github_webhook_secret", "secret")
    payload = b'{"zen":"keep it logically awesome"}'
    signature = github_webhook_service.build_github_webhook_signature(payload, "secret")

    result = await github_webhook_service.handle_github_webhook(payload, "ping", signature)

    assert result.status == "ignored"
    assert result.event == "ping"


@pytest.mark.asyncio
async def test_handle_github_webhook_rejects_invalid_signature(monkeypatch):
    monkeypatch.setattr(github_webhook_service.settings, "github_webhook_secret", "secret")

    payload = b'{"action":"opened"}'

    with pytest.raises(PermissionError):
        await github_webhook_service.handle_github_webhook(payload, "pull_request", "sha256=bad")
