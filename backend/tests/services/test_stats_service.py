from datetime import datetime, timezone

from app.models.analysis import (
    AnalysisContext,
    AnalysisCoverage,
    GithubPrMetadata,
    PrAnalysisResult,
    ScoreSummary,
)
from app.services import stats_service


def build_result(pr_url: str = "https://github.com/acme/reviewer/pull/9") -> PrAnalysisResult:
    return PrAnalysisResult(
        metadata=GithubPrMetadata(
            owner="acme",
            repo="reviewer",
            pull_number=9,
            repo_full_name="acme/reviewer",
            title="Review API contract",
            author="shalv",
            author_avatar_url="https://example.com/avatar.png",
            base_branch="main",
            head_branch="feat/tests",
            head_sha="abc1234567890",
            commits=2,
            additions=22,
            deletions=4,
            changed_files=2,
            html_url=pr_url,
            created_at="2026-03-31T10:00:00Z",
            updated_at="2026-03-31T11:00:00Z",
        ),
        score=88,
        label="high confidence",
        verdict="mergeable with standard review",
        review_focus=["Sensitive paths changed"],
        affected_areas=["shared-core"],
        risk_breakdown=[],
        triggered_signals=[],
        recommendations=[],
        changed_file_groups=[],
        top_risk_files=[],
        commits=[],
        score_summary=ScoreSummary(
            base_score=100,
            total_penalty=12,
            total_relief=0,
            score_version="v1.2-deterministic",
        ),
        analysis_context=AnalysisContext(
            confidence_in_score="high",
            summary="Built from backend evidence.",
            limitations=[],
            data_sources=["GitHub PR metadata"],
            cache_status="live",
            coverage=AnalysisCoverage(
                files_analyzed=2,
                total_files=2,
                patchless_files=0,
                is_partial=False,
                partial_reasons=[],
            ),
        ),
    )


def test_store_and_get_cached_analysis_round_trip(tmp_path, monkeypatch):
    cache_path = tmp_path / "analysis_cache.json"
    stats_path = tmp_path / "stats.json"

    monkeypatch.setattr(stats_service, "_analysis_cache_file", cache_path)
    monkeypatch.setattr(stats_service, "_stats_file", stats_path)
    monkeypatch.setattr(stats_service.settings, "database_url", None)

    result = build_result()

    stats_service.store_cached_analysis(result.metadata.html_url, result)
    cached_result = stats_service.get_cached_analysis(result.metadata.html_url, max_age_seconds=60)

    assert cached_result is not None
    restored_result, age_seconds = cached_result
    assert restored_result.metadata.head_sha == result.metadata.head_sha
    assert restored_result.score == 88
    assert age_seconds >= 0
    assert not (tmp_path / "analysis_cache.json.tmp").exists()


def test_record_analysis_persists_recent_items(tmp_path, monkeypatch):
    cache_path = tmp_path / "analysis_cache.json"
    stats_path = tmp_path / "stats.json"

    monkeypatch.setattr(stats_service, "_analysis_cache_file", cache_path)
    monkeypatch.setattr(stats_service, "_stats_file", stats_path)
    monkeypatch.setattr(stats_service.settings, "database_url", None)

    result = build_result()

    stats_service.record_analysis(result.metadata.html_url, 120.0, "live", result)

    recent_analyses = stats_service.get_recent_analyses()
    public_stats = stats_service.get_public_stats()

    assert recent_analyses[0]["pr_url"] == result.metadata.html_url
    assert recent_analyses[0]["cache_status"] == "live"
    assert public_stats["prs_analyzed"] == 1
    assert public_stats["avg_report_time_seconds"] == 0.1
    assert not (tmp_path / "stats.json.tmp").exists()


def test_get_cached_analysis_returns_none_for_malformed_json(tmp_path, monkeypatch):
    cache_path = tmp_path / "analysis_cache.json"
    cache_path.write_text('{"items": {"broken": {"cached_at": "not-a-date"}}}', encoding="utf-8")

    monkeypatch.setattr(stats_service, "_analysis_cache_file", cache_path)
    monkeypatch.setattr(stats_service.settings, "database_url", None)

    assert stats_service.get_cached_analysis("broken", max_age_seconds=60) is None