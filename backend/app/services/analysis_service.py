import asyncio
import time

from app.core.settings import settings
from app.models.analysis import PrAnalysisResult
from app.services.file_classifier import classify_files
from app.services.github_client import fetch_pr_commits, fetch_pr_files, fetch_pr_metadata
from app.services.pr_url_parser import parse_pr_url
from app.services.result_builder import build_result
from app.services.signal_detector import detect_signals
from app.services.stats_service import get_cached_analysis, record_analysis, store_cached_analysis


analysis_cache: dict[str, tuple[float, PrAnalysisResult]] = {}
inflight_analyses: dict[str, asyncio.Task[PrAnalysisResult]] = {}
request_history: dict[str, list[float]] = {}
inflight_lock = asyncio.Lock()
request_history_lock = asyncio.Lock()


def _cache_age_copy(cached_result: PrAnalysisResult, cache_status: str, age_seconds: float) -> PrAnalysisResult:
    cache_minutes = max(1, round(age_seconds / 60))
    cached_payload = cached_result.model_copy(deep=True)
    cached_payload.analysis_context.cache_status = cache_status

    if cache_status == "fallback":
        cached_payload.analysis_context.confidence_in_score = "low"
        cached_payload.analysis_context.summary = (
            f"Showing a saved review from about {cache_minutes} minute{'s' if cache_minutes != 1 else ''} ago because GitHub could not serve a fresh analysis right now."
        )
        limitations = list(cached_payload.analysis_context.limitations)
        fallback_note = "This response is a stale fallback based on the latest saved successful analysis."
        if fallback_note not in limitations:
            cached_payload.analysis_context.limitations = [fallback_note, *limitations]

    return cached_payload


def read_memory_cached_result(cache_key: str) -> tuple[PrAnalysisResult, float] | None:
    cached_entry = analysis_cache.get(cache_key)
    if not cached_entry:
        return None

    cached_at, cached_result = cached_entry
    age_seconds = time.time() - cached_at
    if age_seconds > settings.cache_ttl_seconds:
        analysis_cache.pop(cache_key, None)
        return None

    return _cache_age_copy(cached_result, "cached", age_seconds), age_seconds


def write_memory_cached_result(cache_key: str, result: PrAnalysisResult, cached_at: float | None = None) -> None:
    analysis_cache[cache_key] = (cached_at or time.time(), result)


def read_saved_cached_result(cache_key: str, max_age_seconds: int) -> tuple[PrAnalysisResult, float] | None:
    cached_entry = get_cached_analysis(cache_key, max_age_seconds)
    if not cached_entry:
        return None

    cached_result, age_seconds = cached_entry
    write_memory_cached_result(cache_key, cached_result, time.time() - age_seconds)
    return cached_result, age_seconds


async def enforce_request_limit(client_key: str) -> None:
    normalized_client_key = client_key.strip() or "anonymous"
    now = time.time()
    window_start = now - settings.analyze_window_seconds

    async with request_history_lock:
        recent_requests = [stamp for stamp in request_history.get(normalized_client_key, []) if stamp >= window_start]
        if len(recent_requests) >= settings.analyze_requests_per_window:
            raise PermissionError("Reviewer is protecting GitHub right now. Please wait a minute before analyzing more pull requests.")

        recent_requests.append(now)
        request_history[normalized_client_key] = recent_requests


async def build_live_analysis(parsed_pr: dict[str, str | int], cache_key: str) -> PrAnalysisResult:
    started_at = time.perf_counter()
    metadata = await fetch_pr_metadata(parsed_pr)
    files, partial_reasons = await fetch_pr_files(parsed_pr, metadata.changed_files)
    commits = await fetch_pr_commits(parsed_pr)
    classified_files = classify_files(files)
    signals = detect_signals(metadata, classified_files)
    result = build_result(
        metadata,
        classified_files,
        commits,
        signals,
        cache_status="live",
        total_files=metadata.changed_files,
        partial_reasons=partial_reasons,
    )
    write_memory_cached_result(cache_key, result)
    store_cached_analysis(cache_key, result)
    duration_ms = (time.perf_counter() - started_at) * 1000
    record_analysis(cache_key, duration_ms, "live", result)
    return result


def build_fallback_result(cache_key: str, error: Exception) -> PrAnalysisResult | None:
    saved_cached_result = read_saved_cached_result(cache_key, settings.stale_cache_ttl_seconds)
    if not saved_cached_result:
        return None

    cached_result, age_seconds = saved_cached_result
    fallback_result = _cache_age_copy(cached_result, "fallback", age_seconds)
    limitations = list(fallback_result.analysis_context.limitations)
    error_note = str(error)
    if error_note and error_note not in limitations:
        fallback_result.analysis_context.limitations = [error_note, *limitations]
    record_analysis(cache_key, 0.0, "fallback", fallback_result)
    return fallback_result


async def analyze_pull_request(pr_url: str, client_key: str) -> PrAnalysisResult:
    await enforce_request_limit(client_key)

    parsed_pr = parse_pr_url(pr_url)
    cache_key = str(parsed_pr["normalized_url"])
    memory_cached_result = read_memory_cached_result(cache_key)

    if memory_cached_result:
        cached_result, _ = memory_cached_result
        record_analysis(cache_key, 0.0, "cached", cached_result)
        return cached_result

    saved_cached_result = read_saved_cached_result(cache_key, settings.cache_ttl_seconds)
    if saved_cached_result:
        cached_result, age_seconds = saved_cached_result
        cached_payload = _cache_age_copy(cached_result, "cached", age_seconds)
        record_analysis(cache_key, 0.0, "cached", cached_payload)
        return cached_payload

    async with inflight_lock:
        inflight_task = inflight_analyses.get(cache_key)
        is_owner = inflight_task is None
        if is_owner:
            inflight_task = asyncio.create_task(build_live_analysis(parsed_pr, cache_key))
            inflight_analyses[cache_key] = inflight_task

    try:
        result = await inflight_task
    except (PermissionError, ConnectionError) as error:
        fallback_result = build_fallback_result(cache_key, error)
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
    record_analysis(cache_key, 0.0, "cached", cached_result)
    return cached_result
