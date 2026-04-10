from datetime import datetime, timedelta, timezone

import pytest

from app.models.auth import GithubAuthSession
from app.services import web_auth_session_service


def test_save_web_auth_session_sets_expiry(tmp_path, monkeypatch):
    store_path = tmp_path / "github_web_sessions.json"
    monkeypatch.setattr(web_auth_session_service, "session_store_file", store_path)
    monkeypatch.setattr(web_auth_session_service.settings, "web_session_ttl_seconds", 3600)

    session_id = web_auth_session_service.save_web_auth_session(
        GithubAuthSession(
            access_token="token",
            login="shalv",
            user_id=7,
            source="web",
        )
    )

    saved_session = web_auth_session_service.load_web_auth_session(session_id)

    assert saved_session is not None
    assert saved_session.created_at
    assert saved_session.expires_at


def test_load_web_auth_session_drops_expired_session(tmp_path, monkeypatch):
    store_path = tmp_path / "github_web_sessions.json"
    monkeypatch.setattr(web_auth_session_service, "session_store_file", store_path)
    expired_session = GithubAuthSession(
        access_token="token",
        login="shalv",
        user_id=7,
        source="web",
        created_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        expires_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    )
    web_auth_session_service.save_session_store({"sessions": {"expired-session": expired_session.model_dump()}})

    loaded_session = web_auth_session_service.load_web_auth_session("expired-session")
    payload = web_auth_session_service.load_session_store()

    assert loaded_session is None
    assert payload == {"sessions": {}}


def test_require_web_auth_session_rejects_missing_session():
    with pytest.raises(PermissionError):
        web_auth_session_service.require_web_auth_session(None)
