# Publish Reviewer CLI

## Before publishing

- Bump the version in `backend/pyproject.toml`.
- Make sure `backend/README.md` matches the current CLI behavior.
- Make sure the root `README.md` reflects the same install and login flow.
- Run the backend CLI tests.
- Remove old build artifacts before creating a new release.
- Build the package locally.
- Verify the generated wheel and source distribution.

## Verify locally

```bash
python -m pytest backend/tests/services/test_auth_session_service.py backend/tests/services/test_cli_main.py backend/tests/services/test_cli_renderer.py backend/tests/services/test_review_publish_service.py backend/tests/services/test_github_client.py backend/tests/services/test_github_renderer.py
python -m build backend
```

## Clean old artifacts

```bash
# PowerShell
if (Test-Path backend/dist) { Remove-Item -Recurse -Force backend/dist }
if (Test-Path backend/build) { Remove-Item -Recurse -Force backend/build }
if (Test-Path backend/reviewer_cli.egg-info) { Remove-Item -Recurse -Force backend/reviewer_cli.egg-info }
```

## Publish

Use an API token with `__token__` as the username:

```bash
# PowerShell
$env:TWINE_USERNAME="__token__"
$env:TWINE_PASSWORD="pypi-your-full-token"
python -m twine upload backend/dist/reviewer_cli-0.1.2*
```

## Recommended user install

```bash
pipx install reviewer-cli
pipx upgrade reviewer-cli
```
