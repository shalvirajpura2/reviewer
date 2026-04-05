import asyncio
from datetime import datetime, timedelta, timezone
import time

from app.core.settings import settings
from app.services.stats_database import connect_database, database_enabled, ensure_database_schema


class RequestLimiter:
    def __init__(self) -> None:
        self.request_history: dict[str, list[float]] = {}
        self.request_history_lock = asyncio.Lock()

    @staticmethod
    def policy_for(action_name: str) -> tuple[int, int, str]:
        if action_name == "preview":
            return (
                settings.preview_window_seconds,
                settings.preview_requests_per_window,
                "Reviewer is protecting GitHub previews right now. Please wait a minute before previewing more pull requests.",
            )

        return (
            settings.analyze_window_seconds,
            settings.analyze_requests_per_window,
            "Reviewer is protecting GitHub right now. Please wait a minute before analyzing more pull requests.",
        )

    async def enforce(self, client_key: str, action_name: str) -> None:
        normalized_client_key = client_key.strip() or "anonymous"
        window_seconds, request_limit, error_message = self.policy_for(action_name)

        if database_enabled():
            await self._enforce_database_limit(normalized_client_key, action_name, window_seconds, request_limit, error_message)
            return

        await self._enforce_memory_limit(normalized_client_key, action_name, window_seconds, request_limit, error_message)

    async def _enforce_memory_limit(
        self,
        normalized_client_key: str,
        action_name: str,
        window_seconds: int,
        request_limit: int,
        error_message: str,
    ) -> None:
        now = time.time()
        history_key = f"{action_name}:{normalized_client_key}"
        window_start = now - window_seconds

        async with self.request_history_lock:
            stale_history_keys = [
                existing_key
                for existing_key, stamps in self.request_history.items()
                if not any(stamp >= window_start for stamp in stamps)
            ]
            for stale_history_key in stale_history_keys:
                self.request_history.pop(stale_history_key, None)

            max_history_keys = max(1, settings.request_history_max_keys)
            if len(self.request_history) >= max_history_keys and history_key not in self.request_history:
                oldest_history_key = min(
                    self.request_history,
                    key=lambda existing_key: self.request_history[existing_key][-1] if self.request_history[existing_key] else 0,
                )
                self.request_history.pop(oldest_history_key, None)

            recent_requests = [stamp for stamp in self.request_history.get(history_key, []) if stamp >= window_start]
            if len(recent_requests) >= request_limit:
                raise PermissionError(error_message)

            recent_requests.append(now)
            self.request_history[history_key] = recent_requests

    async def _enforce_database_limit(
        self,
        normalized_client_key: str,
        action_name: str,
        window_seconds: int,
        request_limit: int,
        error_message: str,
    ) -> None:
        ensure_database_schema()

        history_key = f"{action_name}:{normalized_client_key}"
        window_start = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        prune_before = datetime.now(timezone.utc) - timedelta(seconds=max(window_seconds * 10, 3600))

        with connect_database() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (history_key,))
                cursor.execute(
                    "DELETE FROM request_rate_events WHERE action_name = %s AND client_key = %s AND created_at < %s",
                    (action_name, normalized_client_key, prune_before),
                )
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM request_rate_events
                    WHERE action_name = %s AND client_key = %s AND created_at >= %s
                    """,
                    (action_name, normalized_client_key, window_start),
                )
                recent_request_count = int(cursor.fetchone()[0])
                if recent_request_count >= request_limit:
                    connection.rollback()
                    raise PermissionError(error_message)

                cursor.execute(
                    "INSERT INTO request_rate_events (action_name, client_key) VALUES (%s, %s)",
                    (action_name, normalized_client_key),
                )
            connection.commit()


request_limiter = RequestLimiter()
