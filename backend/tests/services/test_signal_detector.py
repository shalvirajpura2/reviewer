from app.models.analysis import CheckRunSummary, ClassifiedFile, GithubCommitSummary, GithubPrMetadata
from app.services.signal_detector import detect_signals


def build_metadata(**overrides):
    payload = {
        "owner": "acme",
        "repo": "reviewer",
        "pull_number": 42,
        "repo_full_name": "acme/reviewer",
        "title": "Improve review ranking",
        "author": "shalv",
        "author_avatar_url": "https://example.com/avatar.png",
        "base_branch": "main",
        "head_branch": "feature/review",
        "commits": 3,
        "additions": 120,
        "deletions": 24,
        "changed_files": 6,
        "html_url": "https://github.com/acme/reviewer/pull/42",
        "created_at": "2026-03-31T10:00:00Z",
        "updated_at": "2026-03-31T11:00:00Z",
    }
    payload.update(overrides)
    return GithubPrMetadata(**payload)


def build_file(filename: str, areas: list[str], **overrides):
    payload = {
        "filename": filename,
        "status": "modified",
        "additions": 20,
        "deletions": 4,
        "changes": 24,
        "patch": "const value = 1",
        "blob_url": f"https://github.com/acme/reviewer/blob/main/{filename}",
        "previous_filename": None,
        "areas": areas,
        "tags": [area.replace("_", "-") for area in areas if area != "unknown"],
        "is_sensitive": "sensitive" in areas or "config" in areas,
        "blast_radius_weight": 4 if "shared_core" in areas else 2,
        "symbol_hints": [],
    }
    payload.update(overrides)
    return ClassifiedFile(**payload)


def test_detect_signals_returns_docs_only_signal():
    metadata = build_metadata(changed_files=1, additions=8, deletions=2)
    files = [build_file("docs/readme.md", ["docs"], is_sensitive=False, blast_radius_weight=1, patch="# docs")]

    signals = detect_signals(metadata, files, [])

    assert [signal.id for signal in signals] == ["docs_only_change"]


def test_detect_signals_captures_cross_stack_and_test_gaps():
    metadata = build_metadata(changed_files=6, additions=180, deletions=40)
    files = [
        build_file("frontend/src/page.tsx", ["frontend"]),
        build_file("backend/app/routes/analyze.py", ["backend", "api", "sensitive"], is_sensitive=True, blast_radius_weight=4),
        build_file("backend/app/core/settings.py", ["backend", "config", "infra", "sensitive"], is_sensitive=True, blast_radius_weight=4),
        build_file("backend/app/services/scoring_engine.py", ["backend", "shared_core"], blast_radius_weight=4),
        build_file("backend/app/services/github_client.py", ["backend"], patch=None),
        build_file("pnpm-lock.yaml", ["dependency", "lockfile"], is_sensitive=False, blast_radius_weight=1),
    ]
    commits = [GithubCommitSummary(sha="abc1234", message="update review flow", author="shalv")]

    signal_ids = {signal.id for signal in detect_signals(metadata, files, commits)}

    assert "sensitive_paths_changed" in signal_ids
    assert "runtime_and_config_changed" in signal_ids
    assert "cross_stack_change" in signal_ids
    assert "patchless_code_changes" in signal_ids
    assert "no_tests_for_sensitive_change" in signal_ids



def test_detect_signals_captures_failed_ci_checks():
    metadata = build_metadata(changed_files=2, additions=40, deletions=8)
    files = [
        build_file("backend/app/services/reviewer.py", ["backend", "shared_core"], blast_radius_weight=4),
        build_file("backend/tests/services/test_reviewer.py", ["backend", "test"], is_sensitive=False, blast_radius_weight=1),
    ]
    check_runs = [
        CheckRunSummary(
            name="backend tests",
            status="completed",
            conclusion="failure",
            details_url="https://ci.example.com/backend-tests",
        )
    ]

    signal_ids = {signal.id for signal in detect_signals(metadata, files, [], check_runs)}

    assert "ci_checks_failed" in signal_ids
