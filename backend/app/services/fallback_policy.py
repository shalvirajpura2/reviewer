from app.core.settings import settings
from app.models.analysis import GithubPrMetadata, PrAnalysisResult
from app.services.analysis_cache_store import analysis_cache_store
from app.services.stats_service import record_analysis


class FallbackPolicy:
    def build_fallback_result(
        self,
        cache_key: str,
        error: Exception,
        current_metadata: GithubPrMetadata | None = None,
    ) -> PrAnalysisResult | None:
        saved_cached_result = analysis_cache_store.read_saved_cached_result(cache_key, settings.stale_cache_ttl_seconds)
        if not saved_cached_result:
            return None

        cached_result, age_seconds = saved_cached_result
        fallback_result = analysis_cache_store.build_cache_age_copy(cached_result, "fallback", age_seconds)
        limitations = list(fallback_result.analysis_context.limitations)
        error_note = str(error)

        if (
            current_metadata
            and cached_result.metadata.head_sha
            and current_metadata.head_sha
            and cached_result.metadata.head_sha != current_metadata.head_sha
        ):
            revision_note = (
                f"Saved fallback is from commit {cached_result.metadata.head_sha[:7]}, "
                f"but the PR currently points to {current_metadata.head_sha[:7]}."
            )
            if revision_note not in limitations:
                limitations = [revision_note, *limitations]

        if error_note and error_note not in limitations:
            limitations = [error_note, *limitations]

        fallback_result.analysis_context.limitations = limitations
        record_analysis(cache_key, 0.0, "fallback", fallback_result)
        return fallback_result


fallback_policy = FallbackPolicy()