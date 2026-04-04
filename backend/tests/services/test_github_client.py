import httpx
import pytest

from app.services import github_client


class fake_client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.request_count = 0
        self.is_closed = False

    async def get(self, url, headers=None):
        self.request_count += 1
        next_response = self.responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return next_response

    async def aclose(self):
        self.is_closed = True


@pytest.mark.asyncio
async def test_github_fetch_retries_transient_502(monkeypatch):
    client = fake_client([
        httpx.Response(502, json={"message": "bad gateway"}),
        httpx.Response(200, json={"ok": True}),
    ])

    async def fake_get_github_client():
        return client

    monkeypatch.setattr(github_client, "get_github_client", fake_get_github_client)
    async def fake_sleep(delay):
        return None

    monkeypatch.setattr(github_client.asyncio, "sleep", fake_sleep)

    payload = await github_client.github_fetch("/repos/acme/reviewer")

    assert payload == {"ok": True}
    assert client.request_count == 2


@pytest.mark.asyncio
async def test_get_github_client_reuses_open_client():
    await github_client.close_github_client()

    first_client = await github_client.get_github_client()
    second_client = await github_client.get_github_client()

    assert first_client is second_client

    await github_client.close_github_client()
