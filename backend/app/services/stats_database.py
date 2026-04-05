from threading import Lock

from app.core.settings import settings

try:
    import psycopg
except ImportError:
    psycopg = None


db_lock = Lock()
db_initialized = False


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url
    if database_url.startswith("postgres://"):
        return "postgresql://" + database_url[len("postgres://") :]
    return database_url


def database_enabled() -> bool:
    return bool(settings.database_url and psycopg)


def connect_database():
    if not settings.database_url or not psycopg:
        raise RuntimeError("Database support is unavailable.")
    return psycopg.connect(normalize_database_url(settings.database_url))


def ensure_database_schema() -> None:
    global db_initialized

    if not database_enabled() or db_initialized:
        return

    with db_lock:
        if db_initialized:
            return

        with connect_database() as connection:
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
                cursor.execute("ALTER TABLE recent_analyses ADD COLUMN IF NOT EXISTS confidence_in_score TEXT")
                cursor.execute("ALTER TABLE recent_analyses ADD COLUMN IF NOT EXISTS source_updated_at TIMESTAMPTZ")
                cursor.execute("ALTER TABLE recent_analyses ADD COLUMN IF NOT EXISTS files_changed INTEGER")
                cursor.execute("ALTER TABLE recent_analyses ADD COLUMN IF NOT EXISTS files_analyzed INTEGER")
                cursor.execute("ALTER TABLE recent_analyses ADD COLUMN IF NOT EXISTS is_partial BOOLEAN")
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
                cursor.execute("ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS repo_name TEXT")
                cursor.execute("ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS pr_number INTEGER")
                cursor.execute("ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS title TEXT")
                cursor.execute("ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS score INTEGER")
                cursor.execute("ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS verdict TEXT")
                cursor.execute("ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS confidence_label TEXT")
                cursor.execute("ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS confidence_in_score TEXT")
                cursor.execute("ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS source_updated_at TIMESTAMPTZ")
                cursor.execute("ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS files_changed INTEGER")
                cursor.execute("ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS files_analyzed INTEGER")
                cursor.execute("ALTER TABLE cached_analyses ADD COLUMN IF NOT EXISTS is_partial BOOLEAN")
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS request_rate_events (
                        id BIGSERIAL PRIMARY KEY,
                        action_name TEXT NOT NULL,
                        client_key TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS request_rate_events_key_created_at_idx
                    ON request_rate_events (action_name, client_key, created_at DESC)
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

        db_initialized = True
