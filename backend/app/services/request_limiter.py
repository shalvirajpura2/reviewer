import asyncio
import time

from app.core.settings import settings


class RequestLimiter:
    def __init__(self) -> None:
        self.request_history: dict[str, list[float]] = {}
        self.request_history_lock = asyncio.Lock()

    async def enforce(self, client_key: str, action_name: str) -> None:
        normalized_client_key = client_key.strip() or "anonymous"
        now = time.time()

        if action_name == "preview":
            window_seconds = settings.preview_window_seconds
            request_limit = settings.preview_requests_per_window
            error_message = "Reviewer is protecting GitHub previews right now. Please wait a minute before previewing more pull requests."
        else:
            window_seconds = settings.analyze_window_seconds
            request_limit = settings.analyze_requests_per_window
            error_message = "Reviewer is protecting GitHub right now. Please wait a minute before analyzing more pull requests."

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


request_limiter = RequestLimiter()