import time

from app.core.settings import settings
from app.models.analysis import GithubPrMetadata, PrAnalysisResult, PrPreviewResult
from app.services.stats_service import get_cached_analysis


class AnalysisCacheStore:
    def __init__(self) -> None:
        self.analysis_cache: dict[str, tuple[float, PrAnalysisResult]] = {}
        self.preview_cache: dict[str, tuple[float, PrPreviewResult]] = {}

    def build_cache_age_copy(self, cached_result: PrAnalysisResult, cache_status: str, age_seconds: float) -> PrAnalysisResult:
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

    def read_memory_cached_result(self, cache_key: str) -> tuple[PrAnalysisResult, float] | None:
        cached_entry = self.analysis_cache.get(cache_key)
        if not cached_entry:
            return None

        cached_at, cached_result = cached_entry
        age_seconds = time.time() - cached_at
        if age_seconds > settings.cache_ttl_seconds:
            self.analysis_cache.pop(cache_key, None)
            return None

        return self.build_cache_age_copy(cached_result, "cached", age_seconds), age_seconds

    def write_memory_cached_result(self, cache_key: str, result: PrAnalysisResult, cached_at: float | None = None) -> None:
        self.analysis_cache[cache_key] = (cached_at or time.time(), result)

    def read_memory_cached_preview(self, cache_key: str) -> PrPreviewResult | None:
        cached_entry = self.preview_cache.get(cache_key)
        if not cached_entry:
            return None

        cached_at, cached_preview = cached_entry
        if time.time() - cached_at > settings.cache_ttl_seconds:
            self.preview_cache.pop(cache_key, None)
            return None

        return cached_preview.model_copy(deep=True)

    def write_memory_cached_preview(self, cache_key: str, result: PrPreviewResult) -> None:
        self.preview_cache[cache_key] = (time.time(), result)

    def read_saved_cached_result(self, cache_key: str, max_age_seconds: int) -> tuple[PrAnalysisResult, float] | None:
        cached_entry = get_cached_analysis(cache_key, max_age_seconds)
        if not cached_entry:
            return None

        cached_result, age_seconds = cached_entry
        self.write_memory_cached_result(cache_key, cached_result, time.time() - age_seconds)
        return cached_result, age_seconds

    @staticmethod
    def cache_matches_current_revision(cached_result: PrAnalysisResult, metadata: GithubPrMetadata) -> bool:
        cached_head_sha = cached_result.metadata.head_sha.strip()
        current_head_sha = metadata.head_sha.strip()
        return bool(cached_head_sha and current_head_sha and cached_head_sha == current_head_sha)

    @staticmethod
    def refresh_cached_metadata(cached_result: PrAnalysisResult, metadata: GithubPrMetadata) -> PrAnalysisResult:
        refreshed_result = cached_result.model_copy(deep=True)
        refreshed_result.metadata = metadata
        return refreshed_result


analysis_cache_store = AnalysisCacheStore()