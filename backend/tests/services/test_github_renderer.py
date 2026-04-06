from app.models.analysis import CheckRunSummary, ClassifiedFile, GithubCommitSummary, GithubPrMetadata, RiskSignal
from app.renderers.github_renderer import build_github_summary_comment, reviewer_comment_marker
from app.services.result_builder import build_review_analysis


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
        "commits": 2,
        "additions": 80,
        "deletions": 12,
        "changed_files": 3,
        "html_url": "https://github.com/acme/reviewer/pull/7",
        "created_at": "2026-03-31T10:00:00Z",
        "updated_at": "2026-03-31T11:00:00Z",
    }
    payload.update(overrides)
    return GithubPrMetadata(**payload)


def build_file(filename: str, areas: list[str], **overrides):
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
        "areas": areas,
        "tags": [area.replace("_", "-") for area in areas],
        "is_sensitive": "sensitive" in areas,
        "blast_radius_weight": 4 if "shared_core" in areas else 2,
        "symbol_hints": ["imports_changed"] if "shared_core" in areas else [],
    }
    payload.update(overrides)
    return ClassifiedFile(**payload)


def test_build_github_summary_comment_renders_core_sections():
    metadata = build_metadata()
    files = [
        build_file("backend/app/services/github_client.py", ["backend", "shared_core", "sensitive"], is_sensitive=True),
        build_file("backend/tests/services/test_github_client.py", ["backend", "test"], is_sensitive=False, blast_radius_weight=1),
    ]
    commits = [GithubCommitSummary(sha="abc1234", message="tighten analysis", author="shalv")]
    signals = [
        RiskSignal(
            id="sensitive_paths_changed",
            label="Sensitive paths changed",
            severity="high",
            evidence=[files[0].filename],
            score_impact=-16,
            breakdown_key="sensitive_code_risk",
        )
    ]
    check_runs = [
        CheckRunSummary(
            name="backend tests",
            status="completed",
            conclusion="success",
            details_url="https://ci.example.com/backend-tests",
        )
    ]

    review_analysis = build_review_analysis(metadata, files, commits, signals, check_runs=check_runs)
    comment = build_github_summary_comment(review_analysis)

    assert reviewer_comment_marker in comment
    assert "## Reviewer Summary" in comment
    assert "**Verdict:**" in comment
    assert "### Start with" in comment
    assert "`backend/app/services/github_client.py`" in comment
