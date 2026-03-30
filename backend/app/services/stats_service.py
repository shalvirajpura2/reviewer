from datetime import datetime, timezone
from typing import cast
import json
import time
from pathlib import Path
from threading import Lock

from app.core.settings import settings
from app.models.analysis import PrAnalysisResult
from app.services.github_client import fetch_repo_stars

try:
    import psycopg
except ImportError:
    psycopg = None

_stats_file = Path(__file__).resolve().parents[2] / "data" / "stats.json"
_stats_lock = Lock()
_repo_stars_lock = Lock()
_db_lock = Lock()
_repo_stars_cache = {"value": None, "expires_at": 0.0}
_repo_stars_ttl_seconds = 300
_db_initialized = False
_recent_analyses_limit = 8


def _default_stats() -> dict[str, object]:
    return {
        "visitor_count": 0,
        "total_reports_generated": 0,
        "prs_analyzed": 0,
        "deterministic_scoring_rate": 100,
        "total_live_analyses": 0,
        "total_live_analysis_ms": 0.0,
        "seen_pr_urls": [],
        "seen_client_ids": [],
        "recent_analyses": [],
    }


def _read_stats_file() -> dict[str, object]:
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

    if not isinstance(stats.get("seen_client_ids"), list):
        stats["seen_client_ids"] = []

    if not isinstance(stats.get("recent_analyses"), list):
        stats["recent_analyses"] = []

    return stats


def _write_stats_file(stats: dict[str, object]) -> None:
    _stats_file.parent.mkdir(parents=True, exist_ok=True)
    _stats_file.write_text(json.dumps(stats, indent=2), encoding="utf-8")


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url
    if database_url.startswith("postgres://"):
        return "postgresql://" + database_url[len("postgres://") :]
    return database_url


def _database_enabled() -> bool:
    return bool(settings.database_url and psycopg)


def _connect_database():
    if not settings.database_url or not psycopg:
        raise RuntimeError("Database support is unavailable.")
    return psycopg.connect(_normalize_database_url(settings.database_url))


def _ensure_database_schema() -> None:
    global _db_initialized

    if not _database_enabled() or _db_initialized:
        return

    with _db_lock:
        if _db_initialized:
            return

        with _connect_database() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS public_stats (
                        id INTEGER PRIMARY KEY,
                        visitor_count BIGINT NOT NULL DEFAULT 0,
                        total_reports_generated BIGINT NOT NULL DEFAULT 0,
                        prs_analyzed BIGINT NOT NULL DEFAULT 0,
                        deterministic_scoring_rate INTEGER NOT NULL DEFAULT 100,
                        total_live_analyses BIGINT NOT NULL DEFAULT 0,
                        total_live_analysis_ms DOUBLE PRECISION NOT NULL DEFAULT 0
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS seen_pr_urls (
                        pr_url TEXT PRIMARY KEY
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS seen_clients (
                        client_id TEXT PRIMARY KEY
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS recent_analyses (
                        analyzed_at TIMESTAMPTZ NOT NULL,
                        repo_name TEXT NOT NULL,
                        pr_number INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        pr_url TEXT NOT NULL,
                        score INTEGER NOT NULL,
                        verdict TEXT NOT NULL,
                        confidence_label TEXT NOT NULL,
                        cache_status TEXT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    INSERT INTO public_stats (
                        id,
                        visitor_count,
                        total_reports_generated,
                        prs_analyzed,
                        deterministic_scoring_rate,
                        total_live_analyses,
                        total_live_analysis_ms
                    )
                    VALUES (1, 0, 0, 0, 100, 0, 0)
                    ON CONFLICT (id) DO NOTHING
                    """
                )
            connection.commit()

        _db_initialized = True


def _read_stats_database() -> dict[str, object]:
    _ensure_database_schema()

    with _connect_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    visitor_count,
                    total_reports_generated,
                    prs_analyzed,
                    deterministic_scoring_rate,
                    total_live_analyses,
                    total_live_analysis_ms
                FROM public_stats
                WHERE id = 1
                """
            )
            row = cursor.fetchone()
            cursor.execute("SELECT pr_url FROM seen_pr_urls ORDER BY pr_url")
            seen_pr_urls = [item[0] for item in cursor.fetchall()]
            cursor.execute("SELECT client_id FROM seen_clients ORDER BY client_id")
            seen_client_ids = [item[0] for item in cursor.fetchall()]
            cursor.execute(
                """
                SELECT repo_name, pr_number, title, pr_url, score, verdict, confidence_label, analyzed_at, cache_status
                FROM recent_analyses
                ORDER BY analyzed_at DESC
                LIMIT %s
                """,
                (_recent_analyses_limit,),
            )
            recent_analyses = [
                {
                    "repo_name": item[0],
                    "pr_number": int(item[1]),
                    "title": item[2],
                    "pr_url": item[3],
                    "score": int(item[4]),
                    "verdict": item[5],
                    "confidence_label": item[6],
                    "analyzed_at": item[7].isoformat() if item[7] else "",
                    "cache_status": item[8],
                }
                for item in cursor.fetchall()
            ]

    if not row:
        return _default_stats()

    return {
        "visitor_count": int(row[0]),
        "total_reports_generated": int(row[1]),
        "prs_analyzed": int(row[2]),
        "deterministic_scoring_rate": int(row[3]),
        "total_live_analyses": int(row[4]),
        "total_live_analysis_ms": float(row[5]),
        "seen_pr_urls": seen_pr_urls,
        "seen_client_ids": seen_client_ids,
        "recent_analyses": recent_analyses,
    }


def _read_stats() -> dict[str, object]:
    if _database_enabled():
        return _read_stats_database()
    return _read_stats_file()


def _write_stats(stats: dict[str, object]) -> None:
    if _database_enabled():
        _ensure_database_schema()
        seen_pr_urls = list(stats.get("seen_pr_urls", []))
        seen_client_ids = list(stats.get("seen_client_ids", []))
        recent_analyses = list(stats.get("recent_analyses", []))[:_recent_analyses_limit]

        with _connect_database() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE public_stats
                    SET
                        visitor_count = %s,
                        total_reports_generated = %s,
                        prs_analyzed = %s,
                        deterministic_scoring_rate = %s,
                        total_live_analyses = %s,
                        total_live_analysis_ms = %s
                    WHERE id = 1
                    """,
                    (
                        int(stats.get("visitor_count", 0) or 0),
                        int(stats.get("total_reports_generated", 0) or 0),
                        int(stats.get("prs_analyzed", 0) or 0),
                        int(stats.get("deterministic_scoring_rate", 100) or 100),
                        int(stats.get("total_live_analyses", 0) or 0),
                        float(stats.get("total_live_analysis_ms", 0.0) or 0.0),
                    ),
                )
                cursor.execute("DELETE FROM seen_pr_urls")
                if seen_pr_urls:
                    cursor.executemany(
                        "INSERT INTO seen_pr_urls (pr_url) VALUES (%s) ON CONFLICT (pr_url) DO NOTHING",
                        [(pr_url,) for pr_url in seen_pr_urls],
                    )
                cursor.execute("DELETE FROM seen_clients")
                if seen_client_ids:
                    cursor.executemany(
                        "INSERT INTO seen_clients (client_id) VALUES (%s) ON CONFLICT (client_id) DO NOTHING",
                        [(client_id,) for client_id in seen_client_ids],
                    )
                cursor.execute("DELETE FROM recent_analyses")
                if recent_analyses:
                    cursor.executemany(
                        """
                        INSERT INTO recent_analyses (
                            repo_name,
                            pr_number,
                            title,
                            pr_url,
                            score,
                            verdict,
                            confidence_label,
                            analyzed_at,
                            cache_status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            (
                                item.get("repo_name", ""),
                                int(item.get("pr_number", 0) or 0),
                                item.get("title", ""),
                                item.get("pr_url", ""),
                                int(item.get("score", 0) or 0),
                                item.get("verdict", ""),
                                item.get("confidence_label", ""),
                                item.get("analyzed_at", ""),
                                item.get("cache_status", "live"),
                            )
                            for item in recent_analyses
                        ],
                    )
            connection.commit()
        return

    _write_stats_file(stats)


def _recent_analysis_entry(result: PrAnalysisResult, cache_status: str) -> dict[str, object]:
    return {
        "repo_name": result.metadata.repo_full_name,
        "pr_number": result.metadata.pull_number,
        "title": result.metadata.title,
        "pr_url": result.metadata.html_url,
        "score": result.score,
        "verdict": result.verdict,
        "confidence_label": result.label,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "cache_status": cache_status,
    }


def _merge_recent_analyses(existing_items: list[dict[str, object]], next_item: dict[str, object]) -> list[dict[str, object]]:
    merged_items = [next_item]
    next_pr_url = str(next_item.get("pr_url", ""))

    for item in existing_items:
        if str(item.get("pr_url", "")) == next_pr_url:
            continue
        merged_items.append(item)
        if len(merged_items) >= _recent_analyses_limit:
            break

    return merged_items


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


def get_recent_analyses() -> list[dict[str, object]]:
    with _stats_lock:
        stats = _read_stats()
        recent_analyses = list(cast(list[dict[str, object]], stats.get("recent_analyses", [])))
    return recent_analyses[:_recent_analyses_limit]


def record_visit(client_id: str) -> dict[str, int | float | None]:
    normalized_client_id = client_id.strip()
    if not normalized_client_id:
        raise ValueError("Client id is required.")

    with _stats_lock:
        stats = _read_stats()
        seen_client_ids = list(stats.get("seen_client_ids", []))
        if normalized_client_id not in seen_client_ids:
            seen_client_ids.append(normalized_client_id)
            stats["seen_client_ids"] = seen_client_ids
            stats["visitor_count"] = int(stats.get("visitor_count", 0) or 0) + 1
            _write_stats(stats)

    return get_public_stats()


def record_analysis(pr_url: str, duration_ms: float, cache_status: str, result: PrAnalysisResult | None = None) -> None:
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

        if result is not None:
            recent_analyses = list(cast(list[dict[str, object]], stats.get("recent_analyses", [])))
            stats["recent_analyses"] = _merge_recent_analyses(recent_analyses, _recent_analysis_entry(result, cache_status))

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
