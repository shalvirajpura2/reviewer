from pathlib import Path

from app.models.github_bot import GithubBotRepositorySettings
from app.services.json_file_store import read_json_object, write_json_object


settings_store_file = Path(__file__).resolve().parents[2] / "data" / "github_bot_settings.json"


def repository_key(owner: str, repo: str) -> str:
    return f"{owner}/{repo}".lower()


def default_repository_settings() -> GithubBotRepositorySettings:
    return GithubBotRepositorySettings()


def load_repository_settings(owner: str, repo: str) -> GithubBotRepositorySettings:
    payload = read_json_object(settings_store_file, {"repositories": {}})
    repositories = payload.get("repositories", {})
    if not isinstance(repositories, dict):
        return default_repository_settings()

    repository_payload = repositories.get(repository_key(owner, repo), {})
    if not isinstance(repository_payload, dict):
        return default_repository_settings()

    return GithubBotRepositorySettings(**default_repository_settings().model_dump() | repository_payload)


def save_repository_settings(owner: str, repo: str, settings: GithubBotRepositorySettings) -> GithubBotRepositorySettings:
    payload = read_json_object(settings_store_file, {"repositories": {}})
    repositories = payload.get("repositories", {})
    if not isinstance(repositories, dict):
        repositories = {}

    repositories[repository_key(owner, repo)] = settings.model_dump()
    write_json_object(settings_store_file, {"repositories": repositories})
    return settings
