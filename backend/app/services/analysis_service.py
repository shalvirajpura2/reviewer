import asyncio
import time

from app.core.settings import settings
from app.models.analysis import GithubPrMetadata, PrAnalysisResult, PrPreviewResult
from app.services.analysis_cache_store import analysis_cache_store
from app.services.file_classifier import classify_files
from app.services.github_client import fetch_pr_commits, fetch_pr_files, fetch_pr_metadata
from app.services.pr_url_parser import parse_pr_url
from app.services.request_limiter import request_limiter
from app.services.result_builder import build_result
from app.services.signal_detector import detect_signals
from app.services.stats_service import record_analysis, store_cached_analysis


analysis_cache = analysis_cache_store.analysis_cache
preview_cache = analysis_cache_store.preview_cache
request_history = request_limiter.request_history
request_history_lock = request_limiter.request_history_lock
inflight_analyses: dict[str, asyncio.Task[PrAnalysisResult]] = {}
inflight_previews: dict[str, asyncio.Task[PrPreviewResult]] = {}
inflight_lock = asyncio.Lock()
inflight_preview_lock = asyncio.Lock()


def _cache_age_copy(cached_result: PrAnalysisResult, cache_status: str, age_seconds: float) -> PrAnalysisResult:
    return analysis_cache_store.build_cache_age_copy(cached_result, cache_status, age_seconds)


def read_memory_cached_result(cache_key: str) -> tuple[PrAnalysisResult, float] | None:
    return analysis_cache_store.read_memory_cached_result(cache_key)


def write_memory_cached_result(cache_key: str, result: PrAnalysisResult, cached_at: float | None = None) -> None:
    analysis_cache_store.write_memory_cached_result(cache_key, result, cached_at)


def read_memory_cached_preview(cache_key: str) -> PrPreviewResult | None:
    return analysis_cache_store.read_memory_cached_preview(cache_key)


def write_memory_cached_preview(cache_key: str, result: PrPreviewResult) -> None:
    analysis_cache_store.write_memory_cached_preview(cache_key, result)


def read_saved_cached_result(cache_key: str, max_age_seconds: int) -> tuple[PrAnalysisResult, float] | None:
    return analysis_cache_store.read_saved_cached_result(cache_key, max_age_seconds)


def cache_matches_current_revision(cached_result: PrAnalysisResult, metadata: GithubPrMetadata) -> bool:
    return analysis_cache_store.cache_matches_current_revision(cached_result, metadata)


def refresh_cached_metadata(cached_result: PrAnalysisResult, metadata: GithubPrMetadata) -> PrAnalysisResult:
    return analysis_cache_store.refresh_cached_metadata(cached_result, metadata)


async def enforce_request_limit(client_key: str, action_name: str) -> None:
    await request_limiter.enforce(client_key, action_name)


async def build_live_analysis(parsed_pr: dict[str, str | int], cache_key: str, metadata: GithubPrMetadata) -> PrAnalysisResult:
    started_at = time.perf_counter()
    files, partial_reasons = await fetch_pr_files(parsed_pr, metadata.changed_files)
    commits, commit_partial_reasons = await fetch_pr_commits(parsed_pr, metadata.commits)
    classified_files = classify_files(files)
    signals = detect_signals(metadata, classified_files, commits)
    result = build_result(
        metadata,
        classified_files,
        commits,
        signals,
        cache_status="live",
        total_files=metadata.changed_files,
        partial_reasons=[*partial_reasons, *commit_partial_reasons],
    )
    write_memory_cached_result(cache_key, result)
    store_cached_analysis(cache_key, result)
    duration_ms = (time.perf_counter() - started_at) * 1000
    record_analysis(cache_key, duration_ms, "live", result)
    return result


def build_fallback_result(
    cache_key: str,
    error: Exception,
    current_metadata: GithubPrMetadata | None = None,
) -> PrAnalysisResult | None:
    saved_cached_result = read_saved_cached_result(cache_key, settings.stale_cache_ttl_seconds)
    if not saved_cached_result:
        return None

    cached_result, age_seconds = saved_cached_result
    fallback_result = _cache_age_copy(cached_result, "fallback", age_seconds)
    limitations = list(fallback_result.analysis_context.limitations)
    error_note = str(error)

    if (
        current_metadata
        and cached_result.metadata.head_sha
        and current_metadata.head_sha
        and cached_result.metadata.head_sha != current_metadata.head_sha
    ):
        revision_note = (
            f"Saved fallback is from commit {cached_result.metadata.head_sha[:7]}, "
            f"but the PR currently points to {current_metadata.head_sha[:7]}."
        )
        if revision_note not in limitations:
            limitations = [revision_note, *limitations]

    if error_note and error_note not in limitations:
        limitations = [error_note, *limitations]

    fallback_result.analysis_context.limitations = limitations
    record_analysis(cache_key, 0.0, "fallback", fallback_result)
    return fallback_result


async def build_preview(parsed_pr: dict[str, str | int]) -> PrPreviewResult:
    metadata = await fetch_pr_metadata(parsed_pr)
    return PrPreviewResult(metadata=metadata)


async def preview_pull_request(pr_url: str, client_key: str) -> PrPreviewResult:
    await enforce_request_limit(client_key, "preview")

    parsed_pr = parse_pr_url(pr_url)
    cache_key = str(parsed_pr["normalized_url"])
    cached_preview = read_memory_cached_preview(cache_key)

    if cached_preview:
        return cached_preview

    async with inflight_preview_lock:
        inflight_task = inflight_previews.get(cache_key)
        is_owner = inflight_task is None
        if is_owner:
            inflight_task = asyncio.create_task(build_preview(parsed_pr))
            inflight_previews[cache_key] = inflight_task

    try:
        preview_result = await inflight_task
    finally:
        if is_owner:
            async with inflight_preview_lock:
                if inflight_previews.get(cache_key) is inflight_task:
                    inflight_previews.pop(cache_key, None)

    write_memory_cached_preview(cache_key, preview_result)
    return preview_result.model_copy(deep=True)


async def analyze_pull_request(pr_url: str, client_key: str, force_refresh: bool = False) -> PrAnalysisResult:
    await enforce_request_limit(client_key, "analyze")

    parsed_pr = parse_pr_url(pr_url)
    cache_key = str(parsed_pr["normalized_url"])

    try:
        metadata = await fetch_pr_metadata(parsed_pr)
    except (PermissionError, ConnectionError) as error:
        fallback_result = build_fallback_result(cache_key, error)
        if fallback_result is not None:
            return fallback_result
        raise

    memory_cached_result = None if force_refresh else read_memory_cached_result(cache_key)

    if memory_cached_result:
        cached_result, _ = memory_cached_result
        if cache_matches_current_revision(cached_result, metadata):
            cached_result = refresh_cached_metadata(cached_result, metadata)
            record_analysis(cache_key, 0.0, "cached", cached_result)
            return cached_result

    saved_cached_result = None if force_refresh else read_saved_cached_result(cache_key, settings.cache_ttl_seconds)
    if saved_cached_result:
        cached_result, age_seconds = saved_cached_result
        if cache_matches_current_revision(cached_result, metadata):
            cached_payload = _cache_age_copy(cached_result, "cached", age_seconds)
            cached_payload = refresh_cached_metadata(cached_payload, metadata)
            record_analysis(cache_key, 0.0, "cached", cached_payload)
            return cached_payload

    async with inflight_lock:
        inflight_task = inflight_analyses.get(cache_key)
        is_owner = inflight_task is None
        if is_owner:
            inflight_task = asyncio.create_task(build_live_analysis(parsed_pr, cache_key, metadata))
            inflight_analyses[cache_key] = inflight_task

    try:
        result = await inflight_task
    except (PermissionError, ConnectionError) as error:
        fallback_result = build_fallback_result(cache_key, error, metadata)
        if fallback_result is not None:
            return fallback_result
        raise
    finally:
        if is_owner:
            async with inflight_lock:
                if inflight_analyses.get(cache_key) is inflight_task:
                    inflight_analyses.pop(cache_key, None)

    if is_owner:
        return result

    cached_result = result.model_copy(deep=True)
    cached_result.analysis_context.cache_status = "cached"
    cached_result = refresh_cached_metadata(cached_result, metadata)
    record_analysis(cache_key, 0.0, "cached", cached_result)
    return cached_result