import re

from app.cli.main import build_parser, main
from app.models.analysis import AnalysisContext, AnalysisCoverage, GithubPrMetadata, PrAnalysisResult, SafeguardSummary, ScoreSummary
from app.models.auth import GithubAuthSession
from app.models.review_domain import ReviewCommentPublication


ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(value: str) -> str:
    return ansi_pattern.sub("", value)


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


def build_session() -> GithubAuthSession:
    return GithubAuthSession(
        access_token="token-123",
        token_type="bearer",
        scope="read:user public_repo",
        login="shalv",
        user_id=7,
        source="device",
    )


def test_build_parser_defaults_to_text_format():
    parser = build_parser()

    args = parser.parse_args(["analyze", "https://github.com/acme/reviewer/pull/9"])

    assert args.command == "analyze"
    assert args.output_format == "text"
    assert args.force_refresh is False


def test_main_without_command_shows_welcome(capsys):
    exit_code = main([])
    captured = capsys.readouterr()
    output = strip_ansi(captured.out)

    assert exit_code == 0
    assert "r e v i e w e r" in output
    assert "Start Here" in output
    assert "reviewer login" in output


def test_build_parser_supports_login_commands():
    parser = build_parser()

    login_args = parser.parse_args(["login", "--format", "json"])
    whoami_args = parser.parse_args(["whoami"])
    logout_args = parser.parse_args(["logout"])

    assert login_args.command == "login"
    assert login_args.output_format == "json"
    assert whoami_args.command == "whoami"
    assert logout_args.command == "logout"


def test_build_parser_supports_publish_summary_command():
    parser = build_parser()

    args = parser.parse_args(["publish-summary", "https://github.com/acme/reviewer/pull/9", "--format", "json"])

    assert args.command == "publish-summary"
    assert args.output_format == "json"


def test_main_runs_login_command(monkeypatch, capsys):
    async def fake_login_with_device_flow():
        print("[ok] Signed in as @shalv. You can run review commands now.")
        return build_session()

    monkeypatch.setattr("app.cli.main.login_with_device_flow", fake_login_with_device_flow)

    exit_code = main(["login"])
    captured = capsys.readouterr()
    output = strip_ansi(captured.out)

    assert exit_code == 0
    assert "Signed in as @shalv" in output
    assert "Run `reviewer analyze <pr-url>`" in output


def test_main_runs_whoami_command(monkeypatch, capsys):
    async def fake_whoami_session():
        return build_session()

    monkeypatch.setattr("app.cli.main.whoami_session", fake_whoami_session)

    exit_code = main(["whoami"])
    captured = capsys.readouterr()
    output = strip_ansi(captured.out)

    assert exit_code == 0
    assert "Reviewer Session" in output
    assert "Account : @shalv" in output


def test_main_runs_logout_command(monkeypatch, capsys):
    monkeypatch.setattr("app.cli.main.logout_session", lambda: True)

    exit_code = main(["logout"])
    captured = capsys.readouterr()
    output = strip_ansi(captured.out)

    assert exit_code == 0
    assert "Logged out from Reviewer CLI." in output
    assert "reviewer login" in output


def test_main_runs_analyze_command(monkeypatch, capsys):
    async def fake_require_authenticated_session():
        return build_session()

    async def fake_analyze_pull_request(pr_url: str, client_key: str, force_refresh: bool):
        assert pr_url == "https://github.com/acme/reviewer/pull/9"
        assert client_key == "reviewer_cli"
        assert force_refresh is False
        return build_result()

    monkeypatch.setattr("app.cli.main.require_authenticated_session", fake_require_authenticated_session)
    monkeypatch.setattr("app.cli.main.analyze_pull_request", fake_analyze_pull_request)

    exit_code = main(["analyze", "https://github.com/acme/reviewer/pull/9"])
    captured = capsys.readouterr()
    output = strip_ansi(captured.out)

    assert exit_code == 0
    assert "Reviewer Report" in output
    assert "Summary" in output


def test_main_runs_publish_summary_command(monkeypatch, capsys):
    async def fake_require_authenticated_session():
        return build_session()

    async def fake_publish_review_summary(pr_url: str, client_key: str):
        assert pr_url == "https://github.com/acme/reviewer/pull/9"
        assert client_key == "reviewer_cli"
        return ReviewCommentPublication(
            action="updated",
            comment_id=77,
            html_url="https://github.com/acme/reviewer/pull/9#issuecomment-77",
            body="comment body",
        )

    monkeypatch.setattr("app.cli.main.require_authenticated_session", fake_require_authenticated_session)
    monkeypatch.setattr("app.cli.main.publish_review_summary", fake_publish_review_summary)

    exit_code = main(["publish-summary", "https://github.com/acme/reviewer/pull/9"])
    captured = capsys.readouterr()
    output = strip_ansi(captured.out)

    assert exit_code == 0
    assert "GitHub summary comment updated" in output
    assert "Open the pull request" in output


def test_main_returns_error_code_for_known_failures(monkeypatch, capsys):
    async def fake_require_authenticated_session():
        return build_session()

    async def fake_analyze_pull_request(pr_url: str, client_key: str, force_refresh: bool):
        raise ValueError("Unsupported URL format. Paste a direct pull request URL.")

    monkeypatch.setattr("app.cli.main.require_authenticated_session", fake_require_authenticated_session)
    monkeypatch.setattr("app.cli.main.analyze_pull_request", fake_analyze_pull_request)

    exit_code = main(["analyze", "bad-url"])
    captured = capsys.readouterr()
    error_output = strip_ansi(captured.err)

    assert exit_code == 1
    assert "[error] Unsupported URL format" in error_output
