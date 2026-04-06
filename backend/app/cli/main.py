import argparse
import asyncio
import sys

from app.renderers.cli_renderer import render_cli_json, render_cli_text
from app.renderers.cli_ui import render_status, render_welcome
from app.services.analysis_service import analyze_pull_request
from app.services.auth_session_service import login_with_device_flow, logout_session, require_authenticated_session, whoami_session
from app.services.review_publish_service import publish_review_summary


cli_client_key = "reviewer_cli"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reviewer")
    subparsers = parser.add_subparsers(dest="command")

    login_parser = subparsers.add_parser("login", help="Sign in to GitHub for Reviewer CLI")
    login_parser.add_argument("--format", choices=["text", "json"], default="text", dest="output_format")

    whoami_parser = subparsers.add_parser("whoami", help="Show the active GitHub session")
    whoami_parser.add_argument("--format", choices=["text", "json"], default="text", dest="output_format")

    subparsers.add_parser("logout", help="Clear the saved GitHub session")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a public GitHub pull request")
    analyze_parser.add_argument("pr_url", help="Public GitHub pull request URL")
    analyze_parser.add_argument("--format", choices=["text", "json"], default="text", dest="output_format")
    analyze_parser.add_argument("--force-refresh", action="store_true", dest="force_refresh")

    publish_parser = subparsers.add_parser("publish-summary", help="Publish or update the Reviewer summary comment on GitHub")
    publish_parser.add_argument("pr_url", help="Public GitHub pull request URL")
    publish_parser.add_argument("--format", choices=["text", "json"], default="text", dest="output_format")

    return parser


async def run_login(output_format: str) -> int:
    session = await login_with_device_flow()

    if output_format == "json":
        print(session.model_dump_json(indent=2))
    else:
        print(render_status("next", "Run `reviewer analyze <pr-url>` or `reviewer publish-summary <pr-url>`."))

    return 0


async def run_whoami(output_format: str) -> int:
    session = await whoami_session()
    if session is None:
        print(render_status("info", "No active GitHub session."), file=sys.stderr)
        return 1

    if output_format == "json":
        print(session.model_dump_json(indent=2))
    else:
        print("Reviewer Session")
        print("================")
        print(f"Account : @{session.login}")
        print(f"Source  : {session.source}")
        print(f"Scope   : {session.scope or 'default'}")
        print(render_status("next", "Run `reviewer analyze <pr-url>` when you are ready."))

    return 0


def run_logout() -> int:
    if logout_session():
        print(render_status("ok", "Logged out from Reviewer CLI."))
        print(render_status("next", "Run `reviewer login` when you want to connect GitHub again."))
    else:
        print(render_status("info", "No saved Reviewer CLI session was found."))
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
    await require_authenticated_session()
    result = await publish_review_summary(pr_url, cli_client_key)

    if output_format == "json":
        print(result.model_dump_json(indent=2))
    else:
        print(render_status("ok", f"GitHub summary comment {result.action}: {result.html_url or result.comment_id}"))
        print(render_status("next", "Open the pull request to review the published comment."))

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
        print(render_status("error", str(error)), file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
