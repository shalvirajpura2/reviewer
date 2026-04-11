import asyncio

from app.core.settings import settings
from app.models.review_domain import ReviewCommentPublication
from app.renderers.github_renderer import build_github_summary_comment
from app.services.analysis_service import enforce_request_limit
from app.services.file_classifier import classify_files
from app.services.github_app_auth import fetch_installation_access_token, github_app_is_configured
from app.services.github_client import (
    fetch_commit_check_runs,
    fetch_pr_commits,
    fetch_pr_files,
    fetch_pr_metadata,
    upsert_review_summary_comment,
)
from app.services.pr_url_parser import parse_pr_url
from app.services.result_builder import build_review_analysis
from app.services.signal_detector import detect_signals


async def publish_review_summary(pr_url: str, client_key: str, use_backend_publish_token: bool = False) -> ReviewCommentPublication:
    await enforce_request_limit(client_key, "analyze")

    parsed_pr = parse_pr_url(pr_url)
    publish_token = None
    if use_backend_publish_token:
        if github_app_is_configured():
            publish_token = await fetch_installation_access_token(parsed_pr)
        elif settings.reviewer_publish_github_token:
            publish_token = settings.reviewer_publish_github_token
        else:
            raise PermissionError(
                "Reviewer backend publishing is not configured. Set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY or REVIEWER_PUBLISH_GITHUB_TOKEN first."
            )

    metadata = await fetch_pr_metadata(parsed_pr, github_token=publish_token)
    files_task = fetch_pr_files(parsed_pr, metadata.changed_files, github_token=publish_token)
    commits_task = fetch_pr_commits(parsed_pr, metadata.commits, github_token=publish_token)
    check_runs_task = fetch_commit_check_runs(parsed_pr, metadata.head_sha, github_token=publish_token)
    files_result, commits_result, check_runs_result = await asyncio.gather(files_task, commits_task, check_runs_task)
    files, partial_reasons = files_result
    commits, commit_partial_reasons = commits_result
    check_runs, check_partial_reasons = check_runs_result
    classified_files = classify_files(files)
    signals = detect_signals(metadata, classified_files, commits, check_runs)
    review_analysis = build_review_analysis(
        metadata,
        classified_files,
        commits,
        signals,
        check_runs=check_runs,
        cache_status="live",
        total_files=metadata.changed_files,
        partial_reasons=[*partial_reasons, *commit_partial_reasons, *check_partial_reasons],
    )
    comment_body = build_github_summary_comment(review_analysis)

    published_comment = await upsert_review_summary_comment(parsed_pr, comment_body, github_token=publish_token)

    return ReviewCommentPublication(
        action=str(published_comment.get("reviewer_action") or "created"),
        comment_id=int(published_comment.get("id") or 0),
        html_url=published_comment.get("html_url"),
        body=str(published_comment.get("body") or comment_body),
    )
