import pytest

from app.services.request_limiter import RequestLimiter


@pytest.mark.asyncio
async def test_request_limiter_blocks_after_limit_with_memory_store(monkeypatch):
    limiter = RequestLimiter()

    monkeypatch.setattr("app.services.request_limiter.database_enabled", lambda: False)
    monkeypatch.setattr("app.services.request_limiter.settings.analyze_window_seconds", 60)
    monkeypatch.setattr("app.services.request_limiter.settings.analyze_requests_per_window", 2)

    await limiter.enforce("client-a", "analyze")
    await limiter.enforce("client-a", "analyze")

    with pytest.raises(PermissionError):
        await limiter.enforce("client-a", "analyze")


@pytest.mark.asyncio
async def test_request_limiter_uses_preview_policy(monkeypatch):
    limiter = RequestLimiter()

    monkeypatch.setattr("app.services.request_limiter.database_enabled", lambda: False)
    monkeypatch.setattr("app.services.request_limiter.settings.preview_window_seconds", 60)
    monkeypatch.setattr("app.services.request_limiter.settings.preview_requests_per_window", 1)

    await limiter.enforce("client-b", "preview")

    with pytest.raises(PermissionError, match="protecting GitHub previews"):
        await limiter.enforce("client-b", "preview")
