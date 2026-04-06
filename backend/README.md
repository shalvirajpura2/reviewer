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

Preferred setup uses GitHub device login with your GitHub OAuth app client id:

```bash
# Windows PowerShell
$env:GITHUB_CLIENT_ID="your_client_id_here"
```

```bash
# macOS / Linux
export GITHUB_CLIENT_ID="your_client_id_here"
```

Advanced users can still provide a token directly:

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
reviewer login
reviewer whoami
reviewer analyze https://github.com/owner/repo/pull/123
reviewer publish-summary https://github.com/owner/repo/pull/123
reviewer logout
```

Protected commands automatically start the login flow when no valid session is available.
