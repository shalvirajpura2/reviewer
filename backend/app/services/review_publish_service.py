from app.core.settings import settings
from app.models.review_domain import ReviewCommentPublication
from app.renderers.github_renderer import build_github_summary_comment
from app.services.analysis_service import enforce_request_limit
from app.services.file_classifier import classify_files
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
    metadata = await fetch_pr_metadata(parsed_pr)
    files, partial_reasons = await fetch_pr_files(parsed_pr, metadata.changed_files)
    commits, commit_partial_reasons = await fetch_pr_commits(parsed_pr, metadata.commits)
    check_runs, check_partial_reasons = await fetch_commit_check_runs(parsed_pr, metadata.head_sha)
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
    publish_token = settings.reviewer_publish_github_token if use_backend_publish_token else None

    if use_backend_publish_token and not publish_token:
        raise PermissionError("Reviewer backend publishing is not configured. Set REVIEWER_PUBLISH_GITHUB_TOKEN first.")

    published_comment = await upsert_review_summary_comment(parsed_pr, comment_body, github_token=publish_token)

    return ReviewCommentPublication(
        action=str(published_comment.get("reviewer_action") or "created"),
        comment_id=int(published_comment.get("id") or 0),
        html_url=published_comment.get("html_url"),
        body=str(published_comment.get("body") or comment_body),
    )
