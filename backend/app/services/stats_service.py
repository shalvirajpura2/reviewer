import json
import time
from pathlib import Path
from threading import Lock

from app.services.github_client import fetch_repo_stars

_stats_file = Path(__file__).resolve().parents[2] / "data" / "stats.json"
_stats_lock = Lock()
_repo_stars_lock = Lock()
_repo_stars_cache = {"value": None, "expires_at": 0.0}
_repo_stars_ttl_seconds = 300


def _default_stats() -> dict[str, object]:
    return {
        "visitor_count": 0,
        "total_reports_generated": 0,
        "prs_analyzed": 0,
        "deterministic_scoring_rate": 100,
        "total_live_analyses": 0,
        "total_live_analysis_ms": 0.0,
        "seen_pr_urls": [],
    }


def _read_stats() -> dict[str, object]:
    if not _stats_file.exists():
        return _default_stats()

    try:
        payload = json.loads(_stats_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _default_stats()

    stats = _default_stats()
    stats.update(payload if isinstance(payload, dict) else {})

    if not isinstance(stats.get("seen_pr_urls"), list):
        stats["seen_pr_urls"] = []

    return stats


def _write_stats(stats: dict[str, object]) -> None:
    _stats_file.parent.mkdir(parents=True, exist_ok=True)
    _stats_file.write_text(json.dumps(stats, indent=2), encoding="utf-8")


def get_public_stats() -> dict[str, int | float | None]:
    with _stats_lock:
        stats = _read_stats()

    avg_report_time_seconds = None
    total_live_analyses = int(stats.get("total_live_analyses", 0) or 0)
    total_live_analysis_ms = float(stats.get("total_live_analysis_ms", 0.0) or 0.0)

    if total_live_analyses > 0 and total_live_analysis_ms > 0:
        avg_report_time_seconds = round(total_live_analysis_ms / total_live_analyses / 1000, 1)

    return {
        "visitor_count": int(stats.get("visitor_count", 0) or 0),
        "prs_analyzed": int(stats.get("prs_analyzed", 0) or 0),
        "deterministic_scoring_rate": int(stats.get("deterministic_scoring_rate", 100) or 100),
        "avg_report_time_seconds": avg_report_time_seconds,
    }


def record_visit() -> dict[str, int | float | None]:
    with _stats_lock:
        stats = _read_stats()
        stats["visitor_count"] = int(stats.get("visitor_count", 0) or 0) + 1
        _write_stats(stats)

    return get_public_stats()


def record_analysis(pr_url: str, duration_ms: float, cache_status: str) -> None:
    with _stats_lock:
        stats = _read_stats()
        stats["total_reports_generated"] = int(stats.get("total_reports_generated", 0) or 0) + 1

        if cache_status == "live":
            seen_pr_urls = list(stats.get("seen_pr_urls", []))
            if pr_url not in seen_pr_urls:
                seen_pr_urls.append(pr_url)
                stats["seen_pr_urls"] = seen_pr_urls
                stats["prs_analyzed"] = len(seen_pr_urls)

            stats["total_live_analyses"] = int(stats.get("total_live_analyses", 0) or 0) + 1
            stats["total_live_analysis_ms"] = float(stats.get("total_live_analysis_ms", 0.0) or 0.0) + duration_ms

        _write_stats(stats)


async def get_cached_repo_stars(owner: str, repo: str) -> int:
    with _repo_stars_lock:
        cached_value = _repo_stars_cache["value"]
        expires_at = float(_repo_stars_cache["expires_at"] or 0.0)
        if isinstance(cached_value, int) and time.time() < expires_at:
            return cached_value

    try:
        stars = await fetch_repo_stars(owner, repo)
    except Exception:
        if isinstance(cached_value, int):
            return cached_value
        raise

    with _repo_stars_lock:
        _repo_stars_cache["value"] = stars
        _repo_stars_cache["expires_at"] = time.time() + _repo_stars_ttl_seconds

    return stars
