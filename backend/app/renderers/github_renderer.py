from app.models.review_domain import ReviewAnalysis


reviewer_comment_marker = "<!-- reviewer:summary-comment -->"


def build_github_summary_comment(review_analysis: ReviewAnalysis) -> str:
    top_files = review_analysis.top_risk_files[:3]
    recommendations = review_analysis.recommendations[:3]
    findings = review_analysis.findings[:4]

    lines = [
        reviewer_comment_marker,
        "## Reviewer Summary",
        "",
        f"**Verdict:** {review_analysis.verdict}",
        f"**Confidence:** {review_analysis.label} ({review_analysis.score}/100)",
        f"**Safeguards:** {review_analysis.safeguards.summary}",
        "",
        "### Why attention",
    ]

    if findings:
        for finding in findings:
            lines.append(f"- **{finding.title}**: {finding.body}")
    else:
        lines.append("- No material findings were generated for this pull request.")

    lines.extend(["", "### Start with"])
    if top_files:
        for file in top_files:
            lines.append(f"- `{file.filename}`: {file.reasons[0] if file.reasons else 'Review this file first.'}")
    else:
        lines.append("- No high-priority files were identified.")

    lines.extend(["", "### Next checks"])
    if recommendations:
        for recommendation in recommendations:
            lines.append(f"- {recommendation.title}: {recommendation.detail}")
    else:
        lines.append("- No additional follow-up checks were generated.")

    lines.extend(
        [
            "",
            f"Source: `{review_analysis.analysis_context.cache_status}`",
            f"Coverage: `{review_analysis.analysis_context.coverage.files_analyzed}/{review_analysis.analysis_context.coverage.total_files} files analyzed`",
        ]
    )

    return "\n".join(lines)
