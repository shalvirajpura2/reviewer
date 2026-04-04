import pytest

from app.core.settings import settings
from app.models.analysis import AnalysisContext, AnalysisCoverage, GithubPrMetadata, PrAnalysisResult, ScoreSummary
from app.services import analysis_service
from app.services.analysis_service import analysis_cache, enforce_request_limit, request_history, request_history_lock


@pytest.mark.asyncio
async def test_enforce_request_limit_prunes_stale_history(monkeypatch):
    monkeypatch.setattr(settings, "preview_window_seconds", 60)
    monkeypatch.setattr(settings, "preview_requests_per_window", 12)
    monkeypatch.setattr(settings, "request_history_max_keys", 5000)

    async with request_history_lock:
        request_history.clear()
        request_history["preview:stale-client"] = [1.0]

    await enforce_request_limit("fresh-client", "preview")

    async with request_history_lock:
        assert "preview:stale-client" not in request_history
        assert "preview:fresh-client" in request_history


@pytest.mark.asyncio
async def test_enforce_request_limit_caps_history_keys(monkeypatch):
    monkeypatch.setattr(settings, "analyze_window_seconds", 60)
    monkeypatch.setattr(settings, "analyze_requests_per_window", 6)
    monkeypatch.setattr(settings, "request_history_max_keys", 2)

    async with request_history_lock:
        request_history.clear()

    await enforce_request_limit("client-1", "analyze")
    await enforce_request_limit("client-2", "analyze")
    await enforce_request_limit("client-3", "analyze")

    async with request_history_lock:
        assert len(request_history) <= 2
        assert "analyze:client-3" in request_history


@pytest.mark.asyncio
async def test_enforce_request_limit_blocks_after_window_quota(monkeypatch):
    monkeypatch.setattr(settings, "analyze_window_seconds", 60)
    monkeypatch.setattr(settings, "analyze_requests_per_window", 2)
    monkeypatch.setattr(settings, "request_history_max_keys", 5000)

    async with request_history_lock:
        request_history.clear()

    await enforce_request_limit("same-client", "analyze")
    await enforce_request_limit("same-client", "analyze")

    with pytest.raises(PermissionError):
        await enforce_request_limit("same-client", "analyze")


@pytest.mark.asyncio
async def test_analyze_pull_request_skips_cached_result_when_head_sha_changes(monkeypatch):
    metadata_by_call = [
        GithubPrMetadata(
            owner="acme",
            repo="reviewer",
            pull_number=7,
            repo_full_name="acme/reviewer",
            title="First revision",
            author="shalv",
            author_avatar_url="https://example.com/avatar.png",
            base_branch="main",
            head_branch="feature/review",
            head_sha="1111111111111111111111111111111111111111",
            commits=1,
            additions=10,
            deletions=2,
            changed_files=1,
            html_url="https://github.com/acme/reviewer/pull/7",
            created_at="2026-03-31T10:00:00Z",
            updated_at="2026-03-31T11:00:00Z",
        ),
        GithubPrMetadata(
            owner="acme",
            repo="reviewer",
            pull_number=7,
            repo_full_name="acme/reviewer",
            title="Second revision",
            author="shalv",
            author_avatar_url="https://example.com/avatar.png",
            base_branch="main",
            head_branch="feature/review",
            head_sha="2222222222222222222222222222222222222222",
            commits=2,
            additions=14,
            deletions=3,
            changed_files=1,
            html_url="https://github.com/acme/reviewer/pull/7",
            created_at="2026-03-31T10:00:00Z",
            updated_at="2026-03-31T12:00:00Z",
        ),
    ]
    build_calls = []

    async def fake_fetch_pr_metadata(parsed_pr):
        return metadata_by_call.pop(0)

    async def fake_build_live_analysis(parsed_pr, cache_key, metadata):
        build_calls.append(metadata.head_sha)
        result = PrAnalysisResult(
            metadata=metadata,
            score=90 if metadata.head_sha.startswith("1") else 72,
            label="high confidence" if metadata.head_sha.startswith("1") else "moderate confidence",
            verdict="mergeable with standard review" if metadata.head_sha.startswith("1") else "mergeable with focused review",
            review_focus=[],
            affected_areas=[],
            risk_breakdown=[],
            triggered_signals=[],
            recommendations=[],
            changed_file_groups=[],
            top_risk_files=[],
            commits=[],
            score_summary=ScoreSummary(base_score=100, total_penalty=10, total_relief=0, score_version="v1.2-deterministic"),
            analysis_context=AnalysisContext(
                confidence_in_score="high",
                summary="Built from backend evidence.",
                limitations=[],
                data_sources=["GitHub PR metadata"],
                cache_status="live",
                coverage=AnalysisCoverage(files_analyzed=1, total_files=1, patchless_files=0, is_partial=False, partial_reasons=[]),
            ),
        )
        analysis_service.write_memory_cached_result(cache_key, result)
        return result

    async with request_history_lock:
        request_history.clear()
    analysis_cache.clear()

    monkeypatch.setattr(analysis_service, "fetch_pr_metadata", fake_fetch_pr_metadata)
    monkeypatch.setattr(analysis_service, "build_live_analysis", fake_build_live_analysis)
    monkeypatch.setattr(analysis_service, "read_saved_cached_result", lambda cache_key, max_age_seconds: None)
    monkeypatch.setattr(analysis_service, "record_analysis", lambda *args, **kwargs: None)

    first_result = await analysis_service.analyze_pull_request("https://github.com/acme/reviewer/pull/7", "127.0.0.1")
    second_result = await analysis_service.analyze_pull_request("https://github.com/acme/reviewer/pull/7", "127.0.0.1")

    assert first_result.metadata.head_sha == "1111111111111111111111111111111111111111"
    assert second_result.metadata.head_sha == "2222222222222222222222222222222222222222"
    assert build_calls == [
        "1111111111111111111111111111111111111111",
        "2222222222222222222222222222222222222222",
    ]
