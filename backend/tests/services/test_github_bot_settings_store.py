from pathlib import Path

from app.services import github_bot_settings_store


def test_load_repository_record_supports_legacy_settings_payload(tmp_path: Path, monkeypatch):
    store_path = tmp_path / "github_bot_settings.json"
    store_path.write_text(
        '{"repositories":{"acme/reviewer":{"manual_review":true,"automatic_review":true,"review_new_pushes":false}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(github_bot_settings_store, "settings_store_file", store_path)

    settings, activity = github_bot_settings_store.load_repository_record("acme", "reviewer")

    assert settings.manual_review is True
    assert settings.automatic_review is True
    assert settings.review_new_pushes is False
    assert activity.last_pull_number == 0
    assert activity.last_trigger == ""


def test_save_repository_activity_preserves_settings(tmp_path: Path, monkeypatch):
    store_path = tmp_path / "github_bot_settings.json"
    monkeypatch.setattr(github_bot_settings_store, "settings_store_file", store_path)

    github_bot_settings_store.save_repository_settings(
        "acme",
        "reviewer",
        github_bot_settings_store.default_repository_settings().model_copy(update={"automatic_review": True}),
    )
    github_bot_settings_store.save_repository_activity(
        "acme",
        "reviewer",
        github_bot_settings_store.default_repository_activity().model_copy(update={"last_pull_number": 18, "last_trigger": "manual_review"}),
    )

    settings, activity = github_bot_settings_store.load_repository_record("acme", "reviewer")

    assert settings.automatic_review is True
    assert activity.last_pull_number == 18
    assert activity.last_trigger == "manual_review"