from datetime import datetime, timezone
import json
import os
import time
from typing import cast
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
_analysis_cache_file = Path(__file__).resolve().parents[2] / "data" / "analysis_cache.json"
_stats_lock = Lock()
_analysis_cache_lock = Lock()
_repo_stars_lock = Lock()
_db_lock = Lock()
_repo_stars_cache = {"value": None, "expires_at": 0.0}
_repo_stars_ttl_seconds = 300
_db_initialized = False
_recent_analyses_limit = 18


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


def _default_analysis_cache() -> dict[str, object]:
    return {"items": {}}


def _read_json_file(path: Path, fallback: dict[str, object]) -> dict[str, object]:
    if not path.exists():
        return fallback

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback

    if not isinstance(payload, dict):
        return fallback

    merged_payload = dict(fallback)
    merged_payload.update(payload)
    return merged_payload


def _read_stats_file() -> dict[str, object]:
    stats = _read_json_file(_stats_file, _default_stats())

    if not isinstance(stats.get("seen_pr_urls"), list):
        stats["seen_pr_urls"] = []

    if not isinstance(stats.get("seen_client_ids"), list):
        stats["seen_client_ids"] = []

    if not isinstance(stats.get("recent_analyses"), list):
        stats["recent_analyses"] = []

    return stats


def _read_analysis_cache_file() -> dict[str, object]:
    analysis_cache = _read_json_file(_analysis_cache_file, _default_analysis_cache())

    if not isinstance(analysis_cache.get("items"), dict):
        analysis_cache["items"] = {}

    return analysis_cache


def _write_json_file(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")

    with temp_path.open("w", encoding="utf-8") as temp_file:
        json.dump(payload, temp_file, indent=2)
        temp_file.flush()
        os.fsync(temp_file.fileno())

    os.replace(temp_path, path)

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
                        confidence_in_score TEXT,
                        source_updated_at TIMESTAMPTZ,
                        cache_status TEXT NOT NULL,
                        files_changed INTEGER,
                        files_analyzed INTEGER,
                        is_partial BOOLEAN
                    )
                    """
                )
                cursor.execute(
                    "ALTER TABLE recent_analyses ADD COLUMN IF NOT EXISTS confidence_in_score TEXT"
                )
                cursor.execute(
                    "ALTER TABLE recent_analyses ADD COLUMN IF NOT EXISTS source_updated_at TIMESTAMPTZ"
                )
                cursor.execute(
                    "ALTER TABLE recent_analyses ADD COLUMN IF NOT EXISTS files_changed INTEGER"
                )
                cursor.execute(
                    "ALTER TABLE recent_analyses ADD COLUMN IF NOT EXISTS files_analyzed INTEGER"
                )
                cursor.execute(
                    "ALTER TABLE recent_analyses ADD COLUMN IF NOT EXISTS is_partial BOOLEAN"
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cached_analyses (
                        pr_url TEXT PRIMARY KEY,
                        cached_at TIMESTAMPTZ NOT NULL,
                        repo_name TEXT,
                        pr_number INTEGER,
                        title TEXT,
                        score INTEGER,
                        verdict TEXT,
                        confidence_label TEXT,
                        confidence_in_score TEXT,
                        source_updated_at TIMESTAMPTZ,
                        files_changed INTEGER,
                        files_analyzed INTEGER,
                        is_partial BOOLEAN,
                        result_json TEXT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    "ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS repo_name TEXT"
                )
                cursor.execute(
                    "ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS pr_number INTEGER"
                )
                cursor.execute(
                    "ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS title TEXT"
                )
                cursor.execute(
                    "ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS score INTEGER"
                )
                cursor.execute(
                    "ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS verdict TEXT"
                )
                cursor.execute(
                    "ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS confidence_label TEXT"
                )
                cursor.execute(
                    "ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS confidence_in_score TEXT"
                )
                cursor.execute(
                    "ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS source_updated_at TIMESTAMPTZ"
                )
                cursor.execute(
                    "ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS files_changed INTEGER"
                )
                cursor.execute(
                    "ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS files_analyzed INTEGER"
                )
                cursor.execute(
                    "ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS is_partial BOOLEAN"
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


def _read_recent_analyses_database(cursor) -> list[dict[str, object]]:
    cursor.execute(
        """
        SELECT
            repo_name,
            pr_number,
            title,
            pr_url,
            score,
            verdict,
            confidence_label,
            confidence_in_score,
            analyzed_at,
            source_updated_at,
            cache_status,
            files_changed,
            files_analyzed,
            is_partial
        FROM recent_analyses
        ORDER BY analyzed_at DESC
        LIMIT %s
        """,
        (_recent_analyses_limit,),
    )
    return [
        {
            "repo_name": item[0],
            "pr_number": int(item[1]),
            "title": item[2],
            "pr_url": item[3],
            "score": int(item[4]),
            "verdict": item[5],
            "confidence_label": item[6],
            "confidence_in_score": item[7],
            "analyzed_at": item[8].isoformat() if item[8] else "",
            "source_updated_at": item[9].isoformat() if item[9] else None,
            "cache_status": item[10],
            "files_changed": int(item[11]) if item[11] is not None else None,
            "files_analyzed": int(item[12]) if item[12] is not None else None,
            "is_partial": bool(item[13]) if item[13] is not None else None,
        }
        for item in cursor.fetchall()
    ]


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
            recent_analyses = _read_recent_analyses_database(cursor)

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
                            confidence_in_score,
                            analyzed_at,
                            source_updated_at,
                            cache_status,
                            files_changed,
                            files_analyzed,
                            is_partial
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                                item.get("confidence_in_score"),
                                item.get("analyzed_at", ""),
                                item.get("source_updated_at"),
                                item.get("cache_status", "live"),
                                int(item.get("files_changed", 0)) if item.get("files_changed") is not None else None,
                                int(item.get("files_analyzed", 0)) if item.get("files_analyzed") is not None else None,
                                bool(item.get("is_partial")) if item.get("is_partial") is not None else None,
                            )
                            for item in recent_analyses
                        ],
                    )
            connection.commit()
        return

    _write_json_file(_stats_file, stats)


def _serialize_result(result: PrAnalysisResult) -> dict[str, object]:
    return cast(dict[str, object], result.model_dump(mode="json"))


def _deserialize_result(payload: dict[str, object]) -> PrAnalysisResult:
    return PrAnalysisResult.model_validate(payload)


def _analysis_metadata_entry(result: PrAnalysisResult) -> dict[str, object]:
    return {
        "repo_name": result.metadata.repo_full_name,
        "pr_number": result.metadata.pull_number,
        "title": result.metadata.title,
        "score": result.score,
        "verdict": result.verdict,
        "confidence_label": result.label,
        "confidence_in_score": result.analysis_context.confidence_in_score,
        "source_updated_at": result.metadata.updated_at,
        "files_changed": result.metadata.changed_files,
        "files_analyzed": result.analysis_context.coverage.files_analyzed,
        "is_partial": result.analysis_context.coverage.is_partial,
    }


def store_cached_analysis(pr_url: str, result: PrAnalysisResult) -> None:
    cached_at = datetime.now(timezone.utc)
    metadata_entry = _analysis_metadata_entry(result)

    if _database_enabled():
        _ensure_database_schema()
        with _analysis_cache_lock:
            with _connect_database() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO cached_analyses (
                            pr_url,
                            cached_at,
                            repo_name,
                            pr_number,
                            title,
                            score,
                            verdict,
                            confidence_label,
                            confidence_in_score,
                            source_updated_at,
                            files_changed,
                            files_analyzed,
                            is_partial,
                            result_json
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (pr_url)
                        DO UPDATE SET
                            cached_at = EXCLUDED.cached_at,
                            repo_name = EXCLUDED.repo_name,
                            pr_number = EXCLUDED.pr_number,
                            title = EXCLUDED.title,
                            score = EXCLUDED.score,
                            verdict = EXCLUDED.verdict,
                            confidence_label = EXCLUDED.confidence_label,
                            confidence_in_score = EXCLUDED.confidence_in_score,
                            source_updated_at = EXCLUDED.source_updated_at,
                            files_changed = EXCLUDED.files_changed,
                            files_analyzed = EXCLUDED.files_analyzed,
                            is_partial = EXCLUDED.is_partial,
                            result_json = EXCLUDED.result_json
                        """,
                        (
                            pr_url,
                            cached_at,
                            metadata_entry["repo_name"],
                            metadata_entry["pr_number"],
                            metadata_entry["title"],
                            metadata_entry["score"],
                            metadata_entry["verdict"],
                            metadata_entry["confidence_label"],
                            metadata_entry["confidence_in_score"],
                            metadata_entry["source_updated_at"],
                            metadata_entry["files_changed"],
                            metadata_entry["files_analyzed"],
                            metadata_entry["is_partial"],
                            json.dumps(_serialize_result(result)),
                        ),
                    )
                connection.commit()
        return

    with _analysis_cache_lock:
        analysis_cache_payload = _read_analysis_cache_file()
        items = cast(dict[str, object], analysis_cache_payload.get("items", {}))
        items[pr_url] = {
            "cached_at": cached_at.isoformat(),
            "result": _serialize_result(result),
            **metadata_entry,
        }
        analysis_cache_payload["items"] = items
        _write_json_file(_analysis_cache_file, analysis_cache_payload)


def get_cached_analysis(pr_url: str, max_age_seconds: int | None = None) -> tuple[PrAnalysisResult, float] | None:
    if _database_enabled():
        _ensure_database_schema()
        with _analysis_cache_lock:
            with _connect_database() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT cached_at, result_json FROM cached_analyses WHERE pr_url = %s",
                        (pr_url,),
                    )
                    row = cursor.fetchone()
        if not row:
            return None

        cached_at = row[0]
        result_payload = row[1]
        age_seconds = (datetime.now(timezone.utc) - cached_at).total_seconds()
        if max_age_seconds is not None and age_seconds > max_age_seconds:
            return None

        try:
            parsed_payload = json.loads(result_payload)
            return _deserialize_result(parsed_payload), age_seconds
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    with _analysis_cache_lock:
        analysis_cache_payload = _read_analysis_cache_file()
        items = cast(dict[str, object], analysis_cache_payload.get("items", {}))
        raw_item = items.get(pr_url)

    if not isinstance(raw_item, dict):
        return None

    cached_at_raw = raw_item.get("cached_at")
    result_payload = raw_item.get("result")
    if not isinstance(cached_at_raw, str) or not isinstance(result_payload, dict):
        return None

    try:
        cached_at = datetime.fromisoformat(cached_at_raw)
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
    except ValueError:
        return None

    age_seconds = (datetime.now(timezone.utc) - cached_at).total_seconds()
    if max_age_seconds is not None and age_seconds > max_age_seconds:
        return None

    try:
        return _deserialize_result(cast(dict[str, object], result_payload)), age_seconds
    except ValueError:
        return None


def _recent_analysis_entry(result: PrAnalysisResult, cache_status: str) -> dict[str, object]:
    metadata_entry = _analysis_metadata_entry(result)
    return {
        "repo_name": metadata_entry["repo_name"],
        "pr_number": metadata_entry["pr_number"],
        "title": metadata_entry["title"],
        "pr_url": result.metadata.html_url,
        "score": metadata_entry["score"],
        "verdict": metadata_entry["verdict"],
        "confidence_label": metadata_entry["confidence_label"],
        "confidence_in_score": metadata_entry["confidence_in_score"],
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "source_updated_at": metadata_entry["source_updated_at"],
        "cache_status": cache_status,
        "files_changed": metadata_entry["files_changed"],
        "files_analyzed": metadata_entry["files_analyzed"],
        "is_partial": metadata_entry["is_partial"],
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
