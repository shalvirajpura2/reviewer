from app.models.analysis import AnalysisContext, AnalysisCoverage, GithubPrMetadata, PrAnalysisResult, ScoreSummary
from app.services import fallback_policy


def build_result(head_sha: str) -> PrAnalysisResult:
    return PrAnalysisResult(
        metadata=GithubPrMetadata(
            owner="acme",
            repo="reviewer",
            pull_number=7,
            repo_full_name="acme/reviewer",
            title="Saved review",
            author="shalv",
            author_avatar_url="https://example.com/avatar.png",
            base_branch="main",
            head_branch="feature/review",
            head_sha=head_sha,
            commits=1,
            additions=10,
            deletions=2,
            changed_files=1,
            html_url="https://github.com/acme/reviewer/pull/7",
            created_at="2026-03-31T10:00:00Z",
            updated_at="2026-03-31T11:00:00Z",
        ),
        score=88,
        label="high confidence",
        verdict="mergeable with standard review",
        review_focus=[],
        affected_areas=[],
        risk_breakdown=[],
        triggered_signals=[],
        recommendations=[],
        changed_file_groups=[],
        top_risk_files=[],
        commits=[],
        score_summary=ScoreSummary(base_score=100, total_penalty=12, total_relief=0, score_version="v1.2-deterministic"),
        analysis_context=AnalysisContext(
            confidence_in_score="high",
            summary="Built from backend evidence.",
            limitations=["Existing limitation"],
            data_sources=["GitHub PR metadata"],
            cache_status="live",
            coverage=AnalysisCoverage(files_analyzed=1, total_files=1, patchless_files=0, is_partial=False, partial_reasons=[]),
        ),
    )


def test_build_fallback_result_adds_revision_and_error_notes(monkeypatch):
    cached_result = build_result("1111111111111111111111111111111111111111")
    current_metadata = cached_result.metadata.model_copy(update={"head_sha": "2222222222222222222222222222222222222222"})
    recorded_calls = []

    monkeypatch.setattr(
        fallback_policy.analysis_cache_store,
        "read_saved_cached_result",
        lambda cache_key, max_age_seconds: (cached_result, 120),
    )
    monkeypatch.setattr(fallback_policy, "record_analysis", lambda *args: recorded_calls.append(args))

    result = fallback_policy.fallback_policy.build_fallback_result(
        "https://github.com/acme/reviewer/pull/7",
        ConnectionError("GitHub timeout"),
        current_metadata,
    )

    assert result is not None
    assert result.analysis_context.cache_status == "fallback"
    assert result.analysis_context.confidence_in_score == "low"
    assert "GitHub timeout" in result.analysis_context.limitations
    assert any("1111111" in item and "2222222" in item for item in result.analysis_context.limitations)
    assert recorded_calls