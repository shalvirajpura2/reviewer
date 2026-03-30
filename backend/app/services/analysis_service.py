import time

from app.core.settings import settings
from app.models.analysis import PrAnalysisResult
from app.services.file_classifier import classify_files
from app.services.github_client import fetch_pr_commits, fetch_pr_files, fetch_pr_metadata
from app.services.pr_url_parser import parse_pr_url
from app.services.result_builder import build_result
from app.services.signal_detector import detect_signals
from app.services.stats_service import record_analysis


analysis_cache: dict[str, tuple[float, PrAnalysisResult]] = {}


def read_cached_result(cache_key: str) -> PrAnalysisResult | None:
    cached_entry = analysis_cache.get(cache_key)
    if not cached_entry:
        return None

    cached_at, cached_result = cached_entry
    if time.time() - cached_at > settings.cache_ttl_seconds:
        analysis_cache.pop(cache_key, None)
        return None

    cached_payload = cached_result.model_copy(deep=True)
    cached_payload.analysis_context.cache_status = "cached"
    return cached_payload


def store_cached_result(cache_key: str, result: PrAnalysisResult) -> None:
    analysis_cache[cache_key] = (time.time(), result)


async def analyze_pull_request(pr_url: str) -> PrAnalysisResult:
    parsed_pr = parse_pr_url(pr_url)
    cache_key = str(parsed_pr["normalized_url"])
    cached_result = read_cached_result(cache_key)

    if cached_result:
        record_analysis(cache_key, 0.0, "cached", cached_result)
        return cached_result

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
    store_cached_result(cache_key, result)
    duration_ms = (time.perf_counter() - started_at) * 1000
    record_analysis(cache_key, duration_ms, "live", result)
    return result
