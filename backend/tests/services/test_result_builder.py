from app.models.analysis import ClassifiedFile, GithubCommitSummary, GithubPrMetadata, RiskSignal
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
        "patch": "import auth from './auth'",
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
    assert any("patch hunks" in item for item in result.analysis_context.coverage.partial_reasons)
