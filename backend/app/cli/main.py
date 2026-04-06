import argparse
import asyncio
import sys

from app.renderers.cli_renderer import render_cli_json, render_cli_text
from app.services.analysis_service import analyze_pull_request
from app.services.review_publish_service import publish_review_summary


cli_client_key = "reviewer_cli"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reviewer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a public GitHub pull request")
    analyze_parser.add_argument("pr_url", help="Public GitHub pull request URL")
    analyze_parser.add_argument("--format", choices=["text", "json"], default="text", dest="output_format")
    analyze_parser.add_argument("--force-refresh", action="store_true", dest="force_refresh")

    publish_parser = subparsers.add_parser("publish-summary", help="Publish or update the Reviewer summary comment on GitHub")
    publish_parser.add_argument("pr_url", help="Public GitHub pull request URL")
    publish_parser.add_argument("--format", choices=["text", "json"], default="text", dest="output_format")

    return parser


async def run_analyze(pr_url: str, output_format: str, force_refresh: bool) -> int:
    result = await analyze_pull_request(pr_url, cli_client_key, force_refresh)

    if output_format == "json":
        print(render_cli_json(result))
    else:
        print(render_cli_text(result))

    return 0


async def run_publish_summary(pr_url: str, output_format: str) -> int:
    result = await publish_review_summary(pr_url, cli_client_key)

    if output_format == "json":
        print(result.model_dump_json(indent=2))
    else:
        print(f"GitHub summary comment {result.action}: {result.html_url or result.comment_id}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "analyze":
            return asyncio.run(run_analyze(args.pr_url, args.output_format, args.force_refresh))

        if args.command == "publish-summary":
            return asyncio.run(run_publish_summary(args.pr_url, args.output_format))
    except (ValueError, FileNotFoundError, PermissionError, ConnectionError) as error:
        print(str(error), file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
