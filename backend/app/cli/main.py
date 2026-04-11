import argparse
import asyncio
import sys

import httpx

from app.core.settings import settings
from app.models.review_domain import ReviewCommentPublication
from app.renderers.cli_renderer import render_cli_json, render_cli_text
from app.renderers.cli_ui import render_status, render_welcome
from app.services.analysis_service import analyze_pull_request
from app.services.auth_session_service import login_with_device_flow, logout_session, require_authenticated_session, whoami_session
from app.services.review_publish_service import publish_review_summary


cli_client_key = "reviewer_cli"


def error_recovery_steps(command: str | None, error: Exception) -> list[str]:
    message = str(error).lower()

    if "login is required" in message or "authentication is invalid or expired" in message:
        return ["Run `reviewer login` and try again."]

    if "device flow must be explicitly enabled for this app" in message:
        return ["Enable Device Flow for your GitHub OAuth app, or set `GITHUB_CLIENT_ID` to one that already supports it."]

    if "device login could not be started" in message or "client id" in message:
        return ["Check your internet connection, try again, or set `GITHUB_CLIENT_ID` for a custom setup."]

    if "rate limit" in message:
        return ["Wait a minute and try again, or add `GITHUB_TOKEN` for higher GitHub limits."]

    if "temporarily unavailable" in message or "could not be reached" in message or "too long to respond" in message:
        return ["Check your network connection and try again."]

    if "not found" in message:
        if command in {"analyze", "publish-summary"}:
            return ["Verify that the PR URL is public and points directly to `/pull/<number>`."]
        return ["Verify the target exists and try again."]

    if command == "publish-summary" and "backend publishing is not configured" in message:
        return ["Set `REVIEWER_BACKEND_API_BASE` for hosted publishing, or configure the backend bot credentials first."]

    if command == "login":
        return ["Run `reviewer` to review the command list, then try `reviewer login` again."]

    if command == "analyze":
        return ["Check the PR URL and try `reviewer analyze <pr-url>` again."]

    if command == "publish-summary":
        return ["Make sure the repository is accessible and try `reviewer publish-summary <pr-url>` again."]

    if command == "whoami":
        return ["Run `reviewer login` to connect GitHub."]

    return ["Run `reviewer --help` to inspect the available commands and options."]


def print_cli_error(command: str | None, error: Exception) -> None:
    print(render_status("error", str(error)), file=sys.stderr)
    for recovery_step in error_recovery_steps(command, error):
        print(render_status("next", recovery_step), file=sys.stderr)


async def publish_summary_via_backend(pr_url: str) -> ReviewCommentPublication:
    if not settings.reviewer_backend_api_base:
        raise ValueError("Reviewer backend publishing is not configured. Set REVIEWER_BACKEND_API_BASE first.")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{settings.reviewer_backend_api_base}/api/publish-summary",
                json={"pr_url": pr_url},
            )
        except httpx.TimeoutException:
            raise ConnectionError("Reviewer backend took too long to respond. Please try again.")
        except httpx.HTTPError:
            raise ConnectionError("Reviewer backend could not be reached from the CLI.")

    if response.status_code >= 400:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict) and payload.get("message"):
            raise ValueError(str(payload["message"]))

        raise ValueError("Reviewer backend could not publish the GitHub summary comment.")

    return ReviewCommentPublication(**response.json())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reviewer",
        description="Deterministic review for public GitHub pull requests.",
        epilog="Run `reviewer` with no arguments to open the command hub.",
    )
    subparsers = parser.add_subparsers(dest="command")

    login_parser = subparsers.add_parser("login", help="Connect GitHub for protected commands")
    login_parser.add_argument("--format", choices=["text", "json"], default="text", dest="output_format")

    whoami_parser = subparsers.add_parser("whoami", help="Show the active GitHub session")
    whoami_parser.add_argument("--format", choices=["text", "json"], default="text", dest="output_format")

    subparsers.add_parser("logout", help="Clear the saved GitHub session")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a public GitHub pull request")
    analyze_parser.add_argument("pr_url", help="Public GitHub pull request URL")
    analyze_parser.add_argument("--format", choices=["text", "json"], default="text", dest="output_format")
    analyze_parser.add_argument("--force-refresh", action="store_true", dest="force_refresh")

    publish_parser = subparsers.add_parser("publish-summary", help="Publish or update the Reviewer GitHub summary comment")
    publish_parser.add_argument("pr_url", help="Public GitHub pull request URL")
    publish_parser.add_argument("--format", choices=["text", "json"], default="text", dest="output_format")

    return parser


async def run_login(output_format: str) -> int:
    session = await login_with_device_flow()

    if output_format == "json":
        print(session.model_dump_json(indent=2))
    else:
        print(render_status("ok", f"GitHub connected as @{session.login}."))
        print(render_status("next", "Run `reviewer analyze <pr-url>` or `reviewer publish-summary <pr-url>`."))

    return 0


async def run_whoami(output_format: str) -> int:
    session = await whoami_session()
    if session is None:
        print(render_status("info", "No active GitHub session."), file=sys.stderr)
        print(render_status("next", "Run `reviewer login` to connect GitHub."), file=sys.stderr)
        return 1

    if output_format == "json":
        print(session.model_dump_json(indent=2))
    else:
        print("Reviewer Session")
        print("================")
        print(f"Account : @{session.login}")
        print(f"Source  : {session.source}")
        print(f"Scope   : {session.scope or 'default'}")
        print(render_status("ok", f"GitHub session is active for @{session.login}."))
        print(render_status("next", "Run `reviewer analyze <pr-url>` when you are ready."))

    return 0


def run_logout() -> int:
    if logout_session():
        print(render_status("ok", "GitHub session cleared."))
        print(render_status("next", "Run `reviewer login` when you want to connect GitHub again."))
    else:
        print(render_status("info", "No saved GitHub session was found."))
    return 0


async def run_analyze(pr_url: str, output_format: str, force_refresh: bool) -> int:
    await require_authenticated_session()
    result = await analyze_pull_request(pr_url, cli_client_key, force_refresh)

    if output_format == "json":
        print(render_cli_json(result))
    else:
        print(render_cli_text(result))

    return 0


async def run_publish_summary(pr_url: str, output_format: str) -> int:
    if settings.reviewer_backend_api_base:
        result = await publish_summary_via_backend(pr_url)
    else:
        await require_authenticated_session()
        result = await publish_review_summary(pr_url, cli_client_key)

    if output_format == "json":
        print(result.model_dump_json(indent=2))
    else:
        print(render_status("ok", f"GitHub summary comment {result.action}: {result.html_url or result.comment_id}"))
        print(render_status("next", "Open the pull request to review the published summary comment."))

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command is None:
            print(render_welcome())
            return 0

        if args.command == "login":
            return asyncio.run(run_login(args.output_format))

        if args.command == "whoami":
            return asyncio.run(run_whoami(args.output_format))

        if args.command == "logout":
            return run_logout()

        if args.command == "analyze":
            return asyncio.run(run_analyze(args.pr_url, args.output_format, args.force_refresh))

        if args.command == "publish-summary":
            return asyncio.run(run_publish_summary(args.pr_url, args.output_format))
    except (ValueError, FileNotFoundError, PermissionError, ConnectionError) as error:
        print_cli_error(getattr(args, "command", None), error)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
