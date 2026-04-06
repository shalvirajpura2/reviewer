# Publish Reviewer CLI

## Before publishing

- Bump the version in `backend/pyproject.toml`.
- Make sure `backend/README.md` matches the current CLI behavior.
- Run the backend CLI tests.
- Build the package locally.
- Verify the generated wheel and source distribution.

## Verify locally

```bash
python -m pytest backend/tests/services/test_cli_main.py backend/tests/services/test_cli_renderer.py backend/tests/services/test_review_publish_service.py backend/tests/services/test_github_client.py backend/tests/services/test_github_renderer.py
python -m build backend
```

## Publish

```bash
python -m pip install twine
python -m twine upload backend/dist/*
```

## Recommended user install

```bash
pipx install reviewer-cli
```
