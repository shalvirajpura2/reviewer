from app.models.analysis import AnalysisContext, AnalysisCoverage, GithubPrMetadata, PrAnalysisResult, SafeguardSummary, ScoreSummary, TopRiskFile, RecommendationItem
from app.renderers.cli_renderer import render_cli_json, render_cli_text


def build_result() -> PrAnalysisResult:
    return PrAnalysisResult(
        metadata=GithubPrMetadata(
            owner="acme",
            repo="reviewer",
            pull_number=9,
            repo_full_name="acme/reviewer",
            title="Tighten review output",
            author="shalv",
            author_avatar_url="https://example.com/avatar.png",
            base_branch="main",
            head_branch="feat/review",
            commits=3,
            additions=48,
            deletions=10,
            changed_files=2,
            html_url="https://github.com/acme/reviewer/pull/9",
            created_at="2026-04-05T12:00:00Z",
            updated_at="2026-04-05T12:30:00Z",
        ),
        score=82,
        label="high confidence",
        verdict="mergeable with standard review",
        review_focus=["Sensitive paths changed", "Check shared code"],
        affected_areas=["backend", "shared-core"],
        risk_breakdown=[],
        triggered_signals=[],
        recommendations=[
            RecommendationItem(id="owner-review", title="Request owner review", detail="Ask the core maintainer to verify the behavior change.", priority="now"),
        ],
        safeguards=SafeguardSummary(
            ci_state="passing",
            summary="CI checks are passing and this PR includes test changes.",
            checks_total=2,
            checks_passed=2,
            checks_failed=0,
            tests_changed=True,
            missing_safeguards=[],
            check_runs=[],
        ),
        changed_file_groups=[],
        top_risk_files=[
            TopRiskFile(
                filename="backend/app/services/github_client.py",
                risk_level="high",
                reasons=["sensitive execution path touched"],
                reviewer_hints=["backend reviewer"],
                patch_excerpt=[],
                changes=40,
                areas=["backend", "shared_core"],
                is_sensitive=True,
                blob_url="https://github.com/acme/reviewer/blob/main/backend/app/services/github_client.py",
            )
        ],
        commits=[],
        score_summary=ScoreSummary(base_score=100, total_penalty=18, total_relief=0, score_version="v1.2-deterministic"),
        analysis_context=AnalysisContext(
            confidence_in_score="high",
            summary="Built from backend evidence.",
            limitations=[],
            data_sources=["GitHub PR metadata"],
            cache_status="live",
            coverage=AnalysisCoverage(files_analyzed=2, total_files=2, patchless_files=0, is_partial=False, partial_reasons=[]),
        ),
    )


def test_render_cli_text_includes_guided_sections():
    output = render_cli_text(build_result())

    assert "Reviewer Report" in output
    assert "Summary" in output
    assert "Repository : acme/reviewer #9" in output
    assert "Focus Now" in output
    assert "1. Sensitive paths changed" in output
    assert "Start Here" in output
    assert "backend/app/services/github_client.py -> sensitive execution path touched" in output
    assert "Next Steps" in output


def test_render_cli_json_emits_serialized_result():
    output = render_cli_json(build_result())

    assert '"repo_full_name": "acme/reviewer"' in output
    assert '"score": 82' in output
