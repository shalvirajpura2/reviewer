import json

from app.models.analysis import PrAnalysisResult
from app.renderers.cli_ui import join_blocks, render_bullets, render_key_values, render_section, render_steps, render_title


def render_cli_text(result: PrAnalysisResult) -> str:
    summary_items = render_key_values(
        [
            ("Repository", f"{result.metadata.repo_full_name} #{result.metadata.pull_number}"),
            ("Title", result.metadata.title),
            ("Verdict", result.verdict),
            ("Confidence", f"{result.label} ({result.score}/100)"),
            ("Source", result.analysis_context.cache_status),
        ]
    )

    focus_items = render_steps(result.review_focus[:3], "No specific review focus was generated.")

    top_file_items = render_steps(
        [
            f"{file.filename} -> {file.reasons[0] if file.reasons else 'Open this file first.'}"
            for file in result.top_risk_files[:3]
        ],
        "No prioritized files were identified.",
    )

    safeguard_items = render_bullets(
        [
            result.safeguards.summary,
            f"Checks: {result.safeguards.checks_passed}/{result.safeguards.checks_total} passing",
            "Tests changed in this PR." if result.safeguards.tests_changed else "No test changes detected in this PR.",
        ],
        "No safeguard information was generated.",
    )

    next_step_items = render_steps(
        [f"{item.title} -> {item.detail}" for item in result.recommendations[:3]],
        "No follow-up steps were generated.",
    )

    coverage_items = render_bullets(
        [
            f"Files analyzed: {result.analysis_context.coverage.files_analyzed}/{result.analysis_context.coverage.total_files}",
            f"Patchless files: {result.analysis_context.coverage.patchless_files}",
            *result.analysis_context.coverage.partial_reasons[:2],
        ],
        "Full coverage information was not available.",
    )

    return join_blocks(
        render_title("Reviewer Report", "A guided pull request review summary"),
        render_section("Summary", summary_items),
        render_section("Focus Now", focus_items),
        render_section("Start Here", top_file_items),
        render_section("Safeguards", safeguard_items),
        render_section("Next Steps", next_step_items),
        render_section("Coverage", coverage_items),
    )


def render_cli_json(result: PrAnalysisResult) -> str:
    return json.dumps(result.model_dump(mode="json"), indent=2)
