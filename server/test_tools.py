import os
import pytest

from tools import update_long_term_memory, MemoryUpdateMode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def invoke(content: str, mode: str | None = None) -> str:
    """Call the tool via its .invoke() interface (as an agent would)."""
    args = {"content": content}
    if mode is not None:
        args["mode"] = mode
    return update_long_term_memory.invoke(args)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def memory_file(tmp_path, monkeypatch):
    """Set MEMORY_FILE to a fresh temp file and return its path."""
    path = tmp_path / "memory.md"
    monkeypatch.setenv("MEMORY_FILE", str(path))
    return path


# ---------------------------------------------------------------------------
# Missing env var
# ---------------------------------------------------------------------------

class TestMissingEnvVar:
    def test_no_memory_file_env(self, monkeypatch):
        monkeypatch.delenv("MEMORY_FILE", raising=False)
        result = invoke("anything")
        assert result.startswith("Error: MEMORY_FILE environment variable is not set.")


# ---------------------------------------------------------------------------
# Append mode (default)
# ---------------------------------------------------------------------------

class TestAppendMode:
    def test_creates_file_when_missing(self, memory_file):
        result = invoke("# Notes\n")
        assert "append" in result
        assert memory_file.read_text(encoding="utf-8") == "# Notes\n"

    def test_appends_to_empty_file(self, memory_file):
        memory_file.write_text("", encoding="utf-8")
        invoke("first line\n")
        assert memory_file.read_text(encoding="utf-8") == "first line\n"

    def test_appends_when_existing_ends_with_newline(self, memory_file):
        memory_file.write_text("existing\n", encoding="utf-8")
        invoke("new entry\n")
        assert memory_file.read_text(encoding="utf-8") == "existing\nnew entry\n"

    def test_inserts_newline_when_existing_has_no_trailing_newline(self, memory_file):
        memory_file.write_text("existing", encoding="utf-8")
        invoke("new entry\n")
        assert memory_file.read_text(encoding="utf-8") == "existing\nnew entry\n"

    def test_multiple_appends_accumulate(self, memory_file):
        invoke("line 1\n")
        invoke("line 2\n")
        invoke("line 3\n")
        assert memory_file.read_text(encoding="utf-8") == "line 1\nline 2\nline 3\n"

    def test_default_mode_is_append(self, memory_file):
        memory_file.write_text("base\n", encoding="utf-8")
        # Call without specifying mode at all
        update_long_term_memory.invoke({"content": "extra\n"})
        assert memory_file.read_text(encoding="utf-8") == "base\nextra\n"

    def test_explicit_append_string(self, memory_file):
        memory_file.write_text("base\n", encoding="utf-8")
        invoke("extra\n", mode="append")
        assert memory_file.read_text(encoding="utf-8") == "base\nextra\n"

    def test_explicit_append_enum(self, memory_file):
        memory_file.write_text("base\n", encoding="utf-8")
        update_long_term_memory.invoke({"content": "extra\n", "mode": MemoryUpdateMode.append})
        assert memory_file.read_text(encoding="utf-8") == "base\nextra\n"

    def test_returns_success_message(self, memory_file):
        result = invoke("content\n")
        assert "Memory updated successfully" in result
        assert "append" in result
        assert str(memory_file) in result


# ---------------------------------------------------------------------------
# Replace mode
# ---------------------------------------------------------------------------

class TestReplaceMode:
    def test_creates_file_when_missing(self, memory_file):
        invoke("# Fresh\n", mode="replace")
        assert memory_file.read_text(encoding="utf-8") == "# Fresh\n"

    def test_overwrites_existing_content(self, memory_file):
        memory_file.write_text("old content\n", encoding="utf-8")
        invoke("new content\n", mode="replace")
        assert memory_file.read_text(encoding="utf-8") == "new content\n"

    def test_replace_enum(self, memory_file):
        memory_file.write_text("old\n", encoding="utf-8")
        update_long_term_memory.invoke({"content": "new\n", "mode": MemoryUpdateMode.replace})
        assert memory_file.read_text(encoding="utf-8") == "new\n"

    def test_returns_success_message(self, memory_file):
        result = invoke("content\n", mode="replace")
        assert "Memory updated successfully" in result
        assert "replace" in result
        assert str(memory_file) in result


# ---------------------------------------------------------------------------
# Write error
# ---------------------------------------------------------------------------

class TestWriteError:
    def test_unwritable_path_returns_error(self, monkeypatch, tmp_path):
        bad_path = tmp_path / "no_such_dir" / "memory.md"
        monkeypatch.setenv("MEMORY_FILE", str(bad_path))
        result = invoke("anything\n")
        assert result.startswith("Error writing memory file:")

    def test_unwritable_path_replace_returns_error(self, monkeypatch, tmp_path):
        bad_path = tmp_path / "no_such_dir" / "memory.md"
        monkeypatch.setenv("MEMORY_FILE", str(bad_path))
        result = invoke("anything\n", mode="replace")
        assert result.startswith("Error writing memory file:")
