import asyncio
import time

from app.core.settings import settings
from app.models.analysis import GithubPrMetadata, PrAnalysisResult, PrPreviewResult
from app.services.analysis_cache_store import analysis_cache_store
from app.services.fallback_policy import fallback_policy
from app.services.file_classifier import classify_files
from app.services.github_client import fetch_commit_check_runs, fetch_pr_commits, fetch_pr_files, fetch_pr_metadata
from app.services.inflight_task_registry import InflightTaskRegistry
from app.services.pr_url_parser import parse_pr_url
from app.services.request_limiter import request_limiter
from app.services.result_builder import build_result
from app.services.signal_detector import detect_signals
from app.services.stats_service import record_analysis, store_cached_analysis


analysis_cache = analysis_cache_store.analysis_cache
preview_cache = analysis_cache_store.preview_cache
request_history = request_limiter.request_history
request_history_lock = request_limiter.request_history_lock
analysis_inflight_registry = InflightTaskRegistry[PrAnalysisResult]()
preview_inflight_registry = InflightTaskRegistry[PrPreviewResult]()
inflight_analyses = analysis_inflight_registry.inflight_tasks
inflight_previews = preview_inflight_registry.inflight_tasks
inflight_lock = analysis_inflight_registry.inflight_lock
inflight_preview_lock = preview_inflight_registry.inflight_lock


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
    files_task = fetch_pr_files(parsed_pr, metadata.changed_files)
    commits_task = fetch_pr_commits(parsed_pr, metadata.commits)
    check_runs_task = fetch_commit_check_runs(parsed_pr, metadata.head_sha)
    files_result, commits_result, check_runs_result = await asyncio.gather(files_task, commits_task, check_runs_task)
    files, partial_reasons = files_result
    commits, commit_partial_reasons = commits_result
    check_runs, check_partial_reasons = check_runs_result
    classified_files = classify_files(files)
    signals = detect_signals(metadata, classified_files, commits, check_runs)
    result = build_result(
        metadata,
        classified_files,
        commits,
        signals,
        check_runs=check_runs,
        cache_status="live",
        total_files=metadata.changed_files,
        partial_reasons=[*partial_reasons, *commit_partial_reasons, *check_partial_reasons],
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
    return fallback_policy.build_fallback_result(cache_key, error, current_metadata)


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

    inflight_task, is_owner = await preview_inflight_registry.get_or_create(
        cache_key,
        lambda: asyncio.create_task(build_preview(parsed_pr)),
    )

    try:
        preview_result = await inflight_task
    finally:
        await preview_inflight_registry.release(cache_key, inflight_task, is_owner)

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

    inflight_task, is_owner = await analysis_inflight_registry.get_or_create(
        cache_key,
        lambda: asyncio.create_task(build_live_analysis(parsed_pr, cache_key, metadata)),
    )

    try:
        result = await inflight_task
    except (PermissionError, ConnectionError) as error:
        fallback_result = build_fallback_result(cache_key, error, metadata)
        if fallback_result is not None:
            return fallback_result
        raise
    finally:
        await analysis_inflight_registry.release(cache_key, inflight_task, is_owner)

    if is_owner:
        return result

    cached_result = result.model_copy(deep=True)
    cached_result.analysis_context.cache_status = "cached"
    cached_result = refresh_cached_metadata(cached_result, metadata)
    record_analysis(cache_key, 0.0, "cached", cached_result)
    return cached_result