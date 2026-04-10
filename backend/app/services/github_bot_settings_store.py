from pathlib import Path
from threading import Lock

from app.models.github_bot import GithubBotRepositoryActivity, GithubBotRepositorySettings
from app.services.json_file_store import read_json_object, write_json_object


settings_store_file = Path(__file__).resolve().parents[2] / "data" / "github_bot_settings.json"
settings_store_lock = Lock()


def repository_key(owner: str, repo: str) -> str:
    return f"{owner}/{repo}".lower()


def default_repository_settings() -> GithubBotRepositorySettings:
    return GithubBotRepositorySettings()


def default_repository_activity() -> GithubBotRepositoryActivity:
    return GithubBotRepositoryActivity()


def load_repository_record(owner: str, repo: str) -> tuple[GithubBotRepositorySettings, GithubBotRepositoryActivity]:
    with settings_store_lock:
        payload = read_json_object(settings_store_file, {"repositories": {}})
        repositories = payload.get("repositories", {})
        if not isinstance(repositories, dict):
            return default_repository_settings(), default_repository_activity()

        repository_payload = repositories.get(repository_key(owner, repo), {})
        if not isinstance(repository_payload, dict):
            return default_repository_settings(), default_repository_activity()

    settings_payload = repository_payload.get("settings", repository_payload)
    activity_payload = repository_payload.get("activity", {})

    if not isinstance(settings_payload, dict):
        settings_payload = {}

    if not isinstance(activity_payload, dict):
        activity_payload = {}

    settings = GithubBotRepositorySettings(**(default_repository_settings().model_dump() | settings_payload))
    activity = GithubBotRepositoryActivity(**(default_repository_activity().model_dump() | activity_payload))
    return settings, activity


def save_repository_record(
    owner: str,
    repo: str,
    settings: GithubBotRepositorySettings,
    activity: GithubBotRepositoryActivity,
) -> tuple[GithubBotRepositorySettings, GithubBotRepositoryActivity]:
    with settings_store_lock:
        payload = read_json_object(settings_store_file, {"repositories": {}})
        repositories = payload.get("repositories", {})
        if not isinstance(repositories, dict):
            repositories = {}

        repositories[repository_key(owner, repo)] = {
            "settings": settings.model_dump(),
            "activity": activity.model_dump(),
        }
        write_json_object(settings_store_file, {"repositories": repositories})
    return settings, activity


def load_repository_settings(owner: str, repo: str) -> GithubBotRepositorySettings:
    settings, _ = load_repository_record(owner, repo)
    return settings


def load_repository_activity(owner: str, repo: str) -> GithubBotRepositoryActivity:
    _, activity = load_repository_record(owner, repo)
    return activity


def save_repository_settings(owner: str, repo: str, settings: GithubBotRepositorySettings) -> GithubBotRepositorySettings:
    _, activity = load_repository_record(owner, repo)
    save_repository_record(owner, repo, settings, activity)
    return settings


def save_repository_activity(owner: str, repo: str, activity: GithubBotRepositoryActivity) -> GithubBotRepositoryActivity:
    settings, _ = load_repository_record(owner, repo)
    save_repository_record(owner, repo, settings, activity)
    return activity
