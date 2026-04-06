import json

from app.models.analysis import PrAnalysisResult


newline = "\n"


def render_cli_text(result: PrAnalysisResult) -> str:
    top_files = ", ".join(file.filename for file in result.top_risk_files[:3]) or "No prioritized files"
    review_focus = "; ".join(result.review_focus[:3]) or "No specific review focus"
    next_steps = "; ".join(item.title for item in result.recommendations[:3]) or "No follow-up steps generated"

    lines = [
        f"Repository: {result.metadata.repo_full_name} #{result.metadata.pull_number}",
        f"Title: {result.metadata.title}",
        f"Verdict: {result.verdict}",
        f"Confidence label: {result.label}",
        f"Score: {result.score}/100",
        f"Review focus: {review_focus}",
        f"Top files: {top_files}",
        f"Safeguards: {result.safeguards.summary}",
        f"Next steps: {next_steps}",
        f"Source: {result.analysis_context.cache_status}",
    ]

    return newline.join(lines)


def render_cli_json(result: PrAnalysisResult) -> str:
    return json.dumps(result.model_dump(mode="json"), indent=2)
