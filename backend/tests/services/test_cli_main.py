from app.cli.main import build_parser, main
from app.models.analysis import AnalysisContext, AnalysisCoverage, GithubPrMetadata, PrAnalysisResult, SafeguardSummary, ScoreSummary
from app.models.review_domain import ReviewCommentPublication


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
        review_focus=["Sensitive paths changed"],
        affected_areas=["backend", "shared-core"],
        risk_breakdown=[],
        triggered_signals=[],
        recommendations=[],
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
        top_risk_files=[],
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


def test_build_parser_defaults_to_text_format():
    parser = build_parser()

    args = parser.parse_args(["analyze", "https://github.com/acme/reviewer/pull/9"])

    assert args.command == "analyze"
    assert args.output_format == "text"
    assert args.force_refresh is False


def test_build_parser_supports_publish_summary_command():
    parser = build_parser()

    args = parser.parse_args(["publish-summary", "https://github.com/acme/reviewer/pull/9", "--format", "json"])

    assert args.command == "publish-summary"
    assert args.output_format == "json"


def test_main_runs_analyze_command(monkeypatch, capsys):
    async def fake_analyze_pull_request(pr_url: str, client_key: str, force_refresh: bool):
        assert pr_url == "https://github.com/acme/reviewer/pull/9"
        assert client_key == "reviewer_cli"
        assert force_refresh is False
        return build_result()

    monkeypatch.setattr("app.cli.main.analyze_pull_request", fake_analyze_pull_request)

    exit_code = main(["analyze", "https://github.com/acme/reviewer/pull/9"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Repository: acme/reviewer #9" in captured.out


def test_main_runs_publish_summary_command(monkeypatch, capsys):
    async def fake_publish_review_summary(pr_url: str, client_key: str):
        assert pr_url == "https://github.com/acme/reviewer/pull/9"
        assert client_key == "reviewer_cli"
        return ReviewCommentPublication(
            action="updated",
            comment_id=77,
            html_url="https://github.com/acme/reviewer/pull/9#issuecomment-77",
            body="comment body",
        )

    monkeypatch.setattr("app.cli.main.publish_review_summary", fake_publish_review_summary)

    exit_code = main(["publish-summary", "https://github.com/acme/reviewer/pull/9"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "GitHub summary comment updated" in captured.out


def test_main_returns_error_code_for_known_failures(monkeypatch, capsys):
    async def fake_analyze_pull_request(pr_url: str, client_key: str, force_refresh: bool):
        raise ValueError("Unsupported URL format. Paste a direct pull request URL.")

    monkeypatch.setattr("app.cli.main.analyze_pull_request", fake_analyze_pull_request)

    exit_code = main(["analyze", "bad-url"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Unsupported URL format" in captured.err
