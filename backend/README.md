# Reviewer CLI

Reviewer CLI exposes the shared pull request analysis engine as a guided terminal experience.

## Install

After the package is published, install it with `pip`:

```bash
pip install reviewer-cli
```

For local development in this repository:

```bash
pip install -e backend
```

## Configure

Reviewer CLI ships with the default GitHub device login client id, so most users can run `reviewer login` immediately after install. `GITHUB_CLIENT_ID` remains available only as an override for local or self-hosted setups.

Advanced users can still provide a token directly:

```bash
# Windows PowerShell
$env:GITHUB_TOKEN="your_token_here"
```

```bash
# macOS / Linux
export GITHUB_TOKEN="your_token_here"
```

Optional: override where Reviewer stores the local login session.

```bash
# Windows PowerShell
$env:REVIEWER_CONFIG_DIR="C:\Users\you\AppData\Roaming\reviewer-cli"
```

## Usage

Quick start flow:

1. Open the CLI to see the available commands

```bash
reviewer
```

2. Connect GitHub

```bash
reviewer login
```

3. Analyze a pull request

```bash
reviewer analyze https://github.com/owner/repo/pull/123
```

4. Publish or update the GitHub summary comment

```bash
reviewer publish-summary https://github.com/owner/repo/pull/123
```

5. Check session or logout

```bash
reviewer whoami
reviewer logout
```

All commands:

```bash
reviewer login
reviewer whoami
reviewer analyze https://github.com/owner/repo/pull/123
reviewer publish-summary https://github.com/owner/repo/pull/123
reviewer logout
```

## What The CLI Does For Users

- Guides GitHub login step by step with the device link and one-time code.
- Reuses the saved GitHub session automatically so people do not have to log in again on every command.
- Renders reports in readable sections so the next action is obvious.
- Suggests what to do after login, publish, and logout.

Protected commands automatically start the login flow when no valid session is available.

If `REVIEWER_BACKEND_API_BASE` is set, `reviewer publish-summary` uses the hosted Reviewer backend instead of the local GitHub session. Configure `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, and `GITHUB_WEBHOOK_SECRET` on that backend to publish PR comments from a GitHub App bot identity and handle automatic webhook reviews. `REVIEWER_PUBLISH_GITHUB_TOKEN` remains available as a fallback.

