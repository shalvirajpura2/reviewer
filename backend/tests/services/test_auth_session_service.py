import json

from app.models.auth import GithubAuthSession, GithubViewer
from app.services import auth_session_service, github_client


def build_session() -> GithubAuthSession:
    return GithubAuthSession(
        access_token="token-123",
        token_type="bearer",
        scope="read:user public_repo",
        login="shalv",
        user_id=7,
        source="device",
    )


def test_save_and_load_auth_session(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_session_service, "resolve_config_dir", lambda: tmp_path)

    auth_session_service.save_auth_session(build_session())
    loaded = auth_session_service.load_auth_session()

    assert loaded is not None
    assert loaded.login == "shalv"
    assert (tmp_path / "session.json").exists()


def test_logout_session_clears_saved_session(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_session_service, "resolve_config_dir", lambda: tmp_path)
    auth_session_service.save_auth_session(build_session())
    github_client.set_runtime_github_token("token-123")

    cleared = auth_session_service.logout_session()

    assert cleared is True
    assert auth_session_service.load_auth_session() is None
    assert github_client.runtime_github_token is None


def test_resolve_authenticated_session_uses_saved_session(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_session_service, "resolve_config_dir", lambda: tmp_path)
    auth_session_service.save_auth_session(build_session())

    async def fake_fetch_github_viewer(github_token: str):
        assert github_token == "token-123"
        return GithubViewer(login="shalv", user_id=7)

    monkeypatch.setattr(auth_session_service, "fetch_github_viewer", fake_fetch_github_viewer)

    session = __import__("asyncio").run(auth_session_service.resolve_authenticated_session())

    assert session is not None
    assert session.login == "shalv"
    assert github_client.runtime_github_token == "token-123"


def test_require_authenticated_session_triggers_login_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_session_service, "resolve_config_dir", lambda: tmp_path)
    monkeypatch.setattr(auth_session_service.settings, "github_token", "")

    async def fake_login_with_device_flow(print_fn=print):
        return build_session()

    monkeypatch.setattr(auth_session_service, "login_with_device_flow", fake_login_with_device_flow)

    session = __import__("asyncio").run(auth_session_service.require_authenticated_session())

    assert session.login == "shalv"


def test_resolve_authenticated_session_uses_env_token(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_session_service, "resolve_config_dir", lambda: tmp_path)
    monkeypatch.setattr(auth_session_service.settings, "github_token", "env-token")

    async def fake_fetch_github_viewer(github_token: str):
        assert github_token == "env-token"
        return GithubViewer(login="env-user", user_id=8)

    monkeypatch.setattr(auth_session_service, "fetch_github_viewer", fake_fetch_github_viewer)

    session = __import__("asyncio").run(auth_session_service.resolve_authenticated_session())

    assert session is not None
    assert session.source == "env"
    assert session.login == "env-user"
