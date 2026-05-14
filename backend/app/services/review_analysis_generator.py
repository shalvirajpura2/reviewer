import asyncio

from app.models.analysis import GithubPrMetadata
from app.models.review_domain import ReviewAnalysis
from app.services.file_classifier import classify_files
from app.services.github_client import fetch_commit_check_runs, fetch_pr_commits, fetch_pr_files
from app.services.result_builder import build_review_analysis
from app.services.signal_detector import detect_signals


async def generate_review_analysis(
    parsed_pr: dict[str, str | int],
    metadata: GithubPrMetadata,
    github_token: str | None = None,
    cache_status: str = "live",
) -> ReviewAnalysis:
    files_task = fetch_pr_files(parsed_pr, metadata.changed_files, github_token=github_token)
    commits_task = fetch_pr_commits(parsed_pr, metadata.commits, github_token=github_token)
    check_runs_task = fetch_commit_check_runs(parsed_pr, metadata.head_sha, github_token=github_token)
    files_result, commits_result, check_runs_result = await asyncio.gather(files_task, commits_task, check_runs_task)
    files, partial_reasons = files_result
    commits, commit_partial_reasons = commits_result
    check_runs, check_partial_reasons = check_runs_result
    classified_files = classify_files(files)
    signals = detect_signals(metadata, classified_files, commits, check_runs)
    return build_review_analysis(
        metadata,
        classified_files,
        commits,
        signals,
        check_runs=check_runs,
        cache_status=cache_status,
        total_files=metadata.changed_files,
        partial_reasons=[*partial_reasons, *commit_partial_reasons, *check_partial_reasons],
    )
