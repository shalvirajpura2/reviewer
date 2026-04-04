import pytest

from app.core.settings import settings
from app.services.analysis_service import enforce_request_limit, request_history, request_history_lock


@pytest.mark.asyncio
async def test_enforce_request_limit_prunes_stale_history(monkeypatch):
    monkeypatch.setattr(settings, "preview_window_seconds", 60)
    monkeypatch.setattr(settings, "preview_requests_per_window", 12)
    monkeypatch.setattr(settings, "request_history_max_keys", 5000)

    async with request_history_lock:
        request_history.clear()
        request_history["preview:stale-client"] = [1.0]

    await enforce_request_limit("fresh-client", "preview")

    async with request_history_lock:
        assert "preview:stale-client" not in request_history
        assert "preview:fresh-client" in request_history


@pytest.mark.asyncio
async def test_enforce_request_limit_caps_history_keys(monkeypatch):
    monkeypatch.setattr(settings, "analyze_window_seconds", 60)
    monkeypatch.setattr(settings, "analyze_requests_per_window", 6)
    monkeypatch.setattr(settings, "request_history_max_keys", 2)

    async with request_history_lock:
        request_history.clear()

    await enforce_request_limit("client-1", "analyze")
    await enforce_request_limit("client-2", "analyze")
    await enforce_request_limit("client-3", "analyze")

    async with request_history_lock:
        assert len(request_history) <= 2
        assert "analyze:client-3" in request_history


@pytest.mark.asyncio
async def test_enforce_request_limit_blocks_after_window_quota(monkeypatch):
    monkeypatch.setattr(settings, "analyze_window_seconds", 60)
    monkeypatch.setattr(settings, "analyze_requests_per_window", 2)
    monkeypatch.setattr(settings, "request_history_max_keys", 5000)

    async with request_history_lock:
        request_history.clear()

    await enforce_request_limit("same-client", "analyze")
    await enforce_request_limit("same-client", "analyze")

    with pytest.raises(PermissionError):
        await enforce_request_limit("same-client", "analyze")
