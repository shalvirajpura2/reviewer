import hashlib
import hmac
import json

from app.core.settings import settings
from app.models.github_bot import GithubBotWebhookResult
from app.services.github_bot_settings_store import load_repository_settings
from app.services.github_bot_service import trigger_manual_review


supported_pull_request_actions = {"opened", "reopened", "synchronize"}


def github_webhook_is_configured() -> bool:
    return bool(settings.github_webhook_secret)


def build_github_webhook_signature(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_github_webhook_signature(payload: bytes, signature_header: str) -> None:
    if not github_webhook_is_configured():
        raise PermissionError("Reviewer GitHub webhook handling is not configured. Set GITHUB_WEBHOOK_SECRET first.")

    expected_signature = build_github_webhook_signature(payload, settings.github_webhook_secret)
    if not signature_header or not hmac.compare_digest(expected_signature, signature_header.strip()):
        raise PermissionError("GitHub webhook signature is invalid.")


def parse_github_webhook_payload(payload: bytes) -> dict[str, object]:
    try:
        raw_payload = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("GitHub webhook payload is invalid.")

    if not isinstance(raw_payload, dict):
        raise ValueError("GitHub webhook payload is invalid.")

    return raw_payload


def should_trigger_automatic_review(action: str, automatic_review_enabled: bool, review_new_pushes_enabled: bool) -> bool:
    if action in {"opened", "reopened"}:
        return automatic_review_enabled

    if action == "synchronize":
        return review_new_pushes_enabled

    return False


async def handle_github_webhook(payload: bytes, event_name: str, signature_header: str, delivery_id: str = "") -> GithubBotWebhookResult:
    verify_github_webhook_signature(payload, signature_header)

    if event_name == "ping":
        return GithubBotWebhookResult(status="ignored", event=event_name, detail="GitHub webhook ping received.")

    if event_name != "pull_request":
        return GithubBotWebhookResult(status="ignored", event=event_name, detail="GitHub webhook event is not used by Reviewer automation.")

    raw_payload = parse_github_webhook_payload(payload)
    action = str(raw_payload.get("action") or "")
    if action not in supported_pull_request_actions:
        return GithubBotWebhookResult(status="ignored", event=event_name, action=action or None, detail="Pull request action is not configured for Reviewer automation.")

    repository = raw_payload.get("repository")
    pull_request = raw_payload.get("pull_request")
    if not isinstance(repository, dict) or not isinstance(pull_request, dict):
        raise ValueError("GitHub webhook payload is missing repository or pull request details.")

    owner = str(repository.get("owner", {}).get("login") or "")
    repo = str(repository.get("name") or "")
    pull_number = int(pull_request.get("number") or raw_payload.get("number") or 0)
    state = str(pull_request.get("state") or "")

    if not owner or not repo or not pull_number:
        raise ValueError("GitHub webhook payload is missing repository or pull request details.")

    if state and state != "open":
        return GithubBotWebhookResult(status="ignored", event=event_name, action=action, detail="Reviewer only automates open pull requests.")

    repository_settings = load_repository_settings(owner, repo)
    if not should_trigger_automatic_review(action, repository_settings.automatic_review, repository_settings.review_new_pushes):
        return GithubBotWebhookResult(status="ignored", event=event_name, action=action, detail="Repository automation settings do not trigger a review for this event.")

    await trigger_manual_review(owner, repo, pull_number, f"github_webhook:{delivery_id or f'{owner}/{repo}#{pull_number}:{action}'}")
    return GithubBotWebhookResult(
        status="processed",
        event=event_name,
        action=action,
        detail=f"Reviewer posted an automated GitHub summary for {owner}/{repo}#{pull_number}.",
    )
