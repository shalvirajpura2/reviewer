from app.models.analysis import ChangedFile
from app.services import file_classifier


def test_classify_files_marks_runtime_paths_with_symbol_hints(monkeypatch):
    monkeypatch.setattr(file_classifier, "extract_symbol_hints", lambda file: ["authorization", "imports_changed"])

    classified = file_classifier.classify_files(
        [
            ChangedFile(
                filename="frontend/src/auth/session.ts",
                status="modified",
                additions=12,
                deletions=4,
                changes=16,
                patch="import token from './token'",
            )
        ]
    )

    file_item = classified[0]

    assert "frontend" in file_item.areas
    assert "sensitive" in file_item.areas
    assert file_item.is_sensitive is True
    assert file_item.blast_radius_weight >= 4
    assert "auth" in file_item.tags
    assert "authorization" in file_item.tags


def test_classify_files_keeps_docs_changes_low_risk(monkeypatch):
    monkeypatch.setattr(file_classifier, "extract_symbol_hints", lambda file: [])

    classified = file_classifier.classify_files(
        [
            ChangedFile(
                filename="docs/architecture.md",
                status="modified",
                additions=8,
                deletions=1,
                changes=9,
                patch="# docs",
            )
        ]
    )

    file_item = classified[0]

    assert file_item.areas == ["docs"]
    assert file_item.is_sensitive is False
    assert file_item.blast_radius_weight == 1
    assert file_item.tags == ["docs"]



def test_classify_files_marks_suffix_test_modules(monkeypatch):
    monkeypatch.setattr(file_classifier, "extract_symbol_hints", lambda file: [])

    classified = file_classifier.classify_files(
        [
            ChangedFile(
                filename="codex-rs/app-server/src/message_processor/tracing_tests.rs",
                status="modified",
                additions=2,
                deletions=2,
                changes=4,
                patch="assert!(true)",
            )
        ]
    )

    file_item = classified[0]

    assert "test" in file_item.areas
    assert "backend" in file_item.areas
