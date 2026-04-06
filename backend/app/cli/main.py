import argparse
import asyncio
import sys

from app.services.analysis_service import analyze_pull_request
from app.renderers.cli_renderer import render_cli_json, render_cli_text


cli_client_key = "reviewer_cli"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reviewer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a public GitHub pull request")
    analyze_parser.add_argument("pr_url", help="Public GitHub pull request URL")
    analyze_parser.add_argument("--format", choices=["text", "json"], default="text", dest="output_format")
    analyze_parser.add_argument("--force-refresh", action="store_true", dest="force_refresh")

    return parser


async def run_analyze(pr_url: str, output_format: str, force_refresh: bool) -> int:
    result = await analyze_pull_request(pr_url, cli_client_key, force_refresh)

    if output_format == "json":
        print(render_cli_json(result))
    else:
        print(render_cli_text(result))

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        try:
            return asyncio.run(run_analyze(args.pr_url, args.output_format, args.force_refresh))
        except (ValueError, FileNotFoundError, PermissionError, ConnectionError) as error:
            print(str(error), file=sys.stderr)
            return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
