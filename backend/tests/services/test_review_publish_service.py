import asyncio

from app.models.analysis import ChangedFile, CheckRunSummary, GithubCommitSummary, GithubPrMetadata
from app.models.review_domain import ReviewCommentPublication
from app.services.review_publish_service import publish_review_summary


def build_metadata(**overrides):
    payload = {
        "owner": "acme",
        "repo": "reviewer",
        "pull_number": 7,
        "repo_full_name": "acme/reviewer",
        "title": "Tighten backend verdicts",
        "author": "shalv",
        "author_avatar_url": "https://example.com/avatar.png",
        "base_branch": "main",
        "head_branch": "feat/backend",
        "head_sha": "abc1234",
        "commits": 2,
        "additions": 80,
        "deletions": 12,
        "changed_files": 2,
        "html_url": "https://github.com/acme/reviewer/pull/7",
        "created_at": "2026-03-31T10:00:00Z",
        "updated_at": "2026-03-31T11:00:00Z",
    }
    payload.update(overrides)
    return GithubPrMetadata(**payload)


def build_file(filename: str, **overrides):
    payload = {
        "filename": filename,
        "status": "modified",
        "additions": 35,
        "deletions": 5,
        "changes": 40,
        "patch": """@@ -1,2 +1,3 @@
-import auth from './auth'
+import auth from './auth_service'
+export const is_enabled = true""",
        "blob_url": f"https://github.com/acme/reviewer/blob/main/{filename}",
        "previous_filename": None,
    }
    payload.update(overrides)
    return ChangedFile(**payload)


async def fake_enforce_request_limit(client_key: str, action_name: str):
    assert client_key == "reviewer_cli"
    assert action_name == "analyze"


async def fake_fetch_pr_metadata(parsed_pr):
    return build_metadata()


async def fake_fetch_pr_files(parsed_pr, expected_file_count=None):
    return [build_file("backend/app/services/github_client.py")], []


async def fake_fetch_pr_commits(parsed_pr, expected_commit_count=None):
    return [GithubCommitSummary(sha="abc1234", message="tighten analysis", author="shalv")], []


async def fake_fetch_commit_check_runs(parsed_pr, head_sha: str):
    return [CheckRunSummary(name="backend tests", status="completed", conclusion="success")], []


async def fake_upsert_review_summary_comment(parsed_pr, body: str, github_token=None):
    assert body.startswith("<!-- reviewer:summary-comment -->")
    return {
        "reviewer_action": "updated",
        "id": 77,
        "html_url": "https://github.com/acme/reviewer/pull/7#issuecomment-77",
        "body": body,
    }


def test_publish_review_summary_returns_publication_payload(monkeypatch):
    monkeypatch.setattr("app.services.review_publish_service.enforce_request_limit", fake_enforce_request_limit)
    monkeypatch.setattr("app.services.review_publish_service.fetch_pr_metadata", fake_fetch_pr_metadata)
    monkeypatch.setattr("app.services.review_publish_service.fetch_pr_files", fake_fetch_pr_files)
    monkeypatch.setattr("app.services.review_publish_service.fetch_pr_commits", fake_fetch_pr_commits)
    monkeypatch.setattr("app.services.review_publish_service.fetch_commit_check_runs", fake_fetch_commit_check_runs)
    monkeypatch.setattr("app.services.review_publish_service.upsert_review_summary_comment", fake_upsert_review_summary_comment)

    result = asyncio.run(publish_review_summary("https://github.com/acme/reviewer/pull/7", "reviewer_cli"))

    assert isinstance(result, ReviewCommentPublication)
    assert result.action == "updated"
    assert result.comment_id == 77
