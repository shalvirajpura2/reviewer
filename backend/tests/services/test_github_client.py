import httpx
import pytest

from app.renderers.github_renderer import reviewer_comment_marker
from app.services import github_client


class fake_client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.request_count = 0
        self.is_closed = False
        self.requests = []

    async def get(self, url, headers=None):
        self.request_count += 1
        self.requests.append(("GET", url, headers, None))
        next_response = self.responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return next_response

    async def request(self, method, url, headers=None, json=None):
        self.request_count += 1
        self.requests.append((method, url, headers, json))
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


def test_build_headers_uses_runtime_github_token(monkeypatch):
    monkeypatch.setattr(github_client.settings, "github_token", "")
    github_client.set_runtime_github_token("runtime-token")

    headers = github_client.build_headers()

    assert headers["Authorization"] == "Bearer runtime-token"
    github_client.clear_runtime_github_token()


@pytest.mark.asyncio
async def test_fetch_viewer_uses_explicit_token(monkeypatch):
    async def fake_github_fetch(path: str, github_token: str | None = None):
        assert path == "/user"
        assert github_token == "explicit-token"
        return {"login": "shalv", "id": 7}

    monkeypatch.setattr(github_client, "github_fetch", fake_github_fetch)

    payload = await github_client.fetch_viewer("explicit-token")

    assert payload["login"] == "shalv"


@pytest.mark.asyncio
async def test_fetch_commit_check_runs_normalizes_payload(monkeypatch):
    async def fake_github_fetch(path, github_token=None):
        assert path == "/repos/acme/reviewer/commits/abc1234/check-runs?per_page=100"
        return {
            "total_count": 2,
            "check_runs": [
                {
                    "name": "unit tests",
                    "status": "completed",
                    "conclusion": "success",
                    "details_url": "https://ci.example.com/unit-tests",
                },
                {
                    "name": "build",
                    "status": "in_progress",
                    "conclusion": None,
                    "html_url": "https://ci.example.com/build",
                },
            ],
        }

    monkeypatch.setattr(github_client, "github_fetch", fake_github_fetch)

    check_runs, partial_reasons = await github_client.fetch_commit_check_runs(
        {"owner": "acme", "repo": "reviewer", "pull_number": 42},
        "abc1234",
    )

    assert partial_reasons == []
    assert [check_run.name for check_run in check_runs] == ["unit tests", "build"]
    assert check_runs[0].conclusion == "success"
    assert check_runs[1].status == "in_progress"
    assert check_runs[1].details_url == "https://ci.example.com/build"


@pytest.mark.asyncio
async def test_upsert_review_summary_comment_updates_existing_comment(monkeypatch):
    async def fake_fetch_issue_comments(parsed_pr):
        return [{"id": 99, "body": f"{reviewer_comment_marker}\nold comment"}]

    async def fake_update_issue_comment(parsed_pr, comment_id: int, body: str):
        assert parsed_pr == {"owner": "acme", "repo": "reviewer", "pull_number": 9}
        assert comment_id == 99
        assert "new comment" in body
        return {"id": 99, "html_url": "https://github.com/acme/reviewer/pull/9#issuecomment-99", "body": body}

    monkeypatch.setattr(github_client, "fetch_issue_comments", fake_fetch_issue_comments)
    monkeypatch.setattr(github_client, "update_issue_comment", fake_update_issue_comment)

    result = await github_client.upsert_review_summary_comment(
        {"owner": "acme", "repo": "reviewer", "pull_number": 9},
        f"{reviewer_comment_marker}\nnew comment",
    )

    assert result["id"] == 99
    assert result["reviewer_action"] == "updated"


@pytest.mark.asyncio
async def test_upsert_review_summary_comment_creates_when_missing(monkeypatch):
    async def fake_fetch_issue_comments(parsed_pr):
        return []

    async def fake_create_issue_comment(parsed_pr, body: str):
        assert body.startswith(reviewer_comment_marker)
        return {"id": 100, "html_url": "https://github.com/acme/reviewer/pull/9#issuecomment-100", "body": body}

    monkeypatch.setattr(github_client, "fetch_issue_comments", fake_fetch_issue_comments)
    monkeypatch.setattr(github_client, "create_issue_comment", fake_create_issue_comment)

    result = await github_client.upsert_review_summary_comment(
        {"owner": "acme", "repo": "reviewer", "pull_number": 9},
        f"{reviewer_comment_marker}\nnew comment",
    )

    assert result["id"] == 100
    assert result["reviewer_action"] == "created"


