# Reviewer CLI

Reviewer CLI exposes the shared pull request analysis engine as a terminal command.

## Install

After the package is published, install it with `pipx` for the cleanest global command setup:

```bash
pipx install reviewer-cli
```

You can also install it with `pip`:

```bash
pip install reviewer-cli
```

For local development in this repository:

```bash
pip install -e backend
```

## Configure

Set a GitHub token before running analysis commands:

```bash
# Windows PowerShell
$env:GITHUB_TOKEN="your_token_here"
```

```bash
# macOS / Linux
export GITHUB_TOKEN="your_token_here"
```

## Usage

```bash
reviewer analyze https://github.com/owner/repo/pull/123
reviewer analyze https://github.com/owner/repo/pull/123 --format json
reviewer publish-summary https://github.com/owner/repo/pull/123
```
