from app.models.analysis import CheckRunSummary, ClassifiedFile, GithubCommitSummary, GithubPrMetadata, RiskSignal
from app.services.result_builder import build_result


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


def test_build_result_marks_partial_coverage_and_low_confidence():
    metadata = build_metadata()
    files = [
        build_file("backend/app/services/github_client.py", ["backend", "shared_core", "sensitive"], is_sensitive=True),
        build_file("backend/app/core/settings.py", ["backend", "config", "infra", "sensitive"], is_sensitive=True, patch=None),
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

    result = build_result(metadata, files, commits, signals, total_files=3, partial_reasons=["Only part of the PR was fetched."])

    assert result.analysis_context.coverage.is_partial is True
    assert result.analysis_context.coverage.patchless_files == 1
    assert result.analysis_context.confidence_in_score == "low"
    assert result.top_risk_files[0].filename == "backend/app/services/github_client.py"
    assert "backend reviewer" in result.top_risk_files[0].reviewer_hints
    assert result.top_risk_files[0].patch_excerpt == [
        "@@ -1,2 +1,3 @@",
        "-import auth from './auth'",
        "+import auth from './auth_service'",
        "+export const is_enabled = true",
    ]
    assert result.top_risk_files[1].patch_excerpt == []
    assert any("patch hunks" in item for item in result.analysis_context.coverage.partial_reasons)



def test_build_result_includes_safeguards_and_downgrades_missing_ci_confidence():
    metadata = build_metadata()
    files = [
        build_file("backend/app/services/reviewer.py", ["backend", "shared_core"], blast_radius_weight=4),
    ]
    commits = [GithubCommitSummary(sha="abc1234", message="tighten review", author="shalv")]
    signals = []

    result = build_result(metadata, files, commits, signals, check_runs=[])

    assert result.safeguards.ci_state == "missing"
    assert result.safeguards.tests_changed is False
    assert "No test files changed in this PR." in result.safeguards.missing_safeguards
    assert result.analysis_context.confidence_in_score == "low"


def test_build_result_marks_passing_ci_with_test_changes():
    metadata = build_metadata()
    files = [
        build_file("backend/app/services/reviewer.py", ["backend", "shared_core"], blast_radius_weight=4),
        build_file("backend/tests/services/test_reviewer.py", ["backend", "test"], is_sensitive=False, blast_radius_weight=1),
    ]
    commits = [GithubCommitSummary(sha="abc1234", message="tighten review", author="shalv")]
    signals = []
    check_runs = [
        CheckRunSummary(
            name="backend tests",
            status="completed",
            conclusion="success",
            details_url="https://ci.example.com/backend-tests",
        )
    ]

    result = build_result(metadata, files, commits, signals, check_runs=check_runs)

    assert result.safeguards.ci_state == "passing"
    assert result.safeguards.checks_total == 1
    assert result.safeguards.checks_passed == 1
    assert result.safeguards.tests_changed is True
    assert result.analysis_context.confidence_in_score == "high"



def test_build_result_marks_old_merged_pr_ci_as_unavailable():
    metadata = build_metadata(
        merged=True,
        merged_at="2024-10-24T15:42:12Z",
        updated_at="2024-10-24T15:42:12Z",
    )
    files = [
        build_file("packages/tailwindcss/src/utils/decode-arbitrary-value.ts", ["frontend", "shared_core"]),
        build_file("packages/tailwindcss/src/utils/decode-arbitrary-value.test.ts", ["frontend", "test"]),
    ]
    commits = [GithubCommitSummary(sha="75aa966", message="decode arbitrary value", author="adam")]

    result = build_result(metadata, files, commits, [], check_runs=[])

    assert result.safeguards.ci_state == "unavailable"
    assert result.safeguards.summary == "GitHub no longer exposes CI checks for this historical merged PR."
    assert result.analysis_context.confidence_in_score == "medium"
