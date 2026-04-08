import pytest

from app.services import github_app_auth


def test_normalize_github_app_private_key_rehydrates_newlines():
    normalized = github_app_auth.normalize_github_app_private_key("-----BEGIN KEY-----\\nline2\\n-----END KEY-----")

    assert "\n" in normalized
    assert "line2" in normalized


def test_build_github_app_jwt_uses_settings_and_private_key(monkeypatch):
    captured = {}

    def fake_encode(payload, private_key, algorithm):
        captured["payload"] = payload
        captured["private_key"] = private_key
        captured["algorithm"] = algorithm
        return "jwt-token"

    monkeypatch.setattr(github_app_auth.settings, "github_app_id", "3297155")
    monkeypatch.setattr(github_app_auth.settings, "github_app_private_key", "-----BEGIN KEY-----\\nline2\\n-----END KEY-----")
    monkeypatch.setattr(github_app_auth.jwt, "encode", fake_encode)

    token = github_app_auth.build_github_app_jwt(now_timestamp=1000)

    assert token == "jwt-token"
    assert captured["payload"]["iss"] == "3297155"
    assert captured["payload"]["iat"] == 940
    assert captured["payload"]["exp"] == 1540
    assert captured["algorithm"] == "RS256"
    assert captured["private_key"].startswith("-----BEGIN KEY-----")


@pytest.mark.asyncio
async def test_fetch_installation_access_token_uses_repo_installation(monkeypatch):
    monkeypatch.setattr(github_app_auth, "build_github_app_jwt", lambda: "jwt-token")

    async def fake_github_fetch(path: str, github_token=None, action_name=None):
        assert path == "/repos/acme/reviewer/installation"
        assert github_token == "jwt-token"
        return {"id": 44}

    async def fake_github_send(method: str, path: str, payload: dict, action_name: str, github_token=None):
        assert method == "POST"
        assert path == "/app/installations/44/access_tokens"
        assert payload == {}
        assert github_token == "jwt-token"
        return {"token": "installation-token"}

    monkeypatch.setattr(github_app_auth, "github_fetch", fake_github_fetch)
    monkeypatch.setattr(github_app_auth, "github_send", fake_github_send)

    token = await github_app_auth.fetch_installation_access_token({"owner": "acme", "repo": "reviewer", "pull_number": 9})

    assert token == "installation-token"


@pytest.mark.asyncio
async def test_fetch_app_installations_uses_app_jwt(monkeypatch):
    monkeypatch.setattr(github_app_auth, "build_github_app_jwt", lambda: "jwt-token")

    async def fake_github_fetch(path: str, github_token=None, action_name=None):
        assert path == "/app/installations?per_page=100"
        assert github_token == "jwt-token"
        return [{"id": 44}, {"id": 45}]

    monkeypatch.setattr(github_app_auth, "github_fetch", fake_github_fetch)

    payload = await github_app_auth.fetch_app_installations()

    assert len(payload) == 2


@pytest.mark.asyncio
async def test_fetch_installation_repositories_uses_installation_token(monkeypatch):
    async def fake_fetch_installation_access_token_by_id(installation_id: int):
        assert installation_id == 44
        return "installation-token"

    async def fake_github_fetch(path: str, github_token=None, action_name=None):
        assert path == "/installation/repositories?per_page=100"
        assert github_token == "installation-token"
        return {"repositories": [{"full_name": "acme/reviewer"}]}

    monkeypatch.setattr(github_app_auth, "fetch_installation_access_token_by_id", fake_fetch_installation_access_token_by_id)
    monkeypatch.setattr(github_app_auth, "github_fetch", fake_github_fetch)

    payload = await github_app_auth.fetch_installation_repositories(44)

    assert payload == [{"full_name": "acme/reviewer"}]
