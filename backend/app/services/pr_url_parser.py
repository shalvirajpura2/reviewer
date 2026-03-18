from urllib.parse import urlparse


def parse_pr_url(pr_url: str) -> dict[str, str | int]:
    parsed_url = urlparse(pr_url.strip())
    path_parts = [part for part in parsed_url.path.split("/") if part]

    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError("Unsupported URL format. Paste a direct pull request URL.")

    if parsed_url.netloc not in {"github.com", "www.github.com"}:
        raise ValueError("Unsupported host. Please use a public GitHub pull request URL.")

    if len(path_parts) < 4 or path_parts[2] != "pull":
        raise ValueError("Unsupported URL format. Paste a direct pull request URL.")

    owner = path_parts[0]
    repo = path_parts[1]

    try:
        pull_number = int(path_parts[3])
    except ValueError as error:
        raise ValueError("The pull request URL is missing a valid pull number.") from error

    if pull_number <= 0:
        raise ValueError("The pull request URL is missing a valid pull number.")

    return {
        "owner": owner,
        "repo": repo,
        "pull_number": pull_number,
        "normalized_url": f"https://github.com/{owner}/{repo}/pull/{pull_number}",
    }
