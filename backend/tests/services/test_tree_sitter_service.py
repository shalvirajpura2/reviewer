from app.models.analysis import ChangedFile
from app.services.tree_sitter_service import build_parseable_patch_source, extract_symbol_hints


def test_build_parseable_patch_source_removes_diff_markers():
    source_text = build_parseable_patch_source(
        """@@ -1,3 +1,4 @@
-import old_auth
+import new_auth
+
 def login():
+    return new_auth.token()
-    return old_auth.token()
"""
    )

    assert "@@" not in source_text
    assert "import new_auth" in source_text
    assert "return new_auth.token()" in source_text
    assert "old_auth.token()" not in source_text


def test_extract_symbol_hints_reads_rebuilt_patch_source():
    file_item = ChangedFile(
        filename="backend/app/services/auth_service.py",
        status="modified",
        additions=2,
        deletions=1,
        changes=3,
        patch="""@@ -1,2 +1,3 @@
-from auth import old_token
+from auth import session_token
+admin_permission = session_token
""",
    )

    hints = extract_symbol_hints(file_item)

    assert "session" in hints
    assert "permission" in hints