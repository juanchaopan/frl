import os
import re
from enum import Enum

from langchain_core.tools import tool

SECTION_HEADINGS = {
    "words": "## Words",
    "phrases": "## Phrases",
    "expressions": "## Sentence Expressions",
}

_INITIAL_MEMORY = """\
## Words

## Phrases

## Sentence Expressions
"""


class MemorySection(str, Enum):
    words = "words"
    phrases = "phrases"
    expressions = "expressions"


def _ensure_file(memory_file: str) -> str:
    """Return file contents, creating the file with empty sections if missing."""
    if not os.path.exists(memory_file):
        with open(memory_file, "w", encoding="utf-8") as f:
            f.write(_INITIAL_MEMORY)
        return _INITIAL_MEMORY
    with open(memory_file, "r", encoding="utf-8") as f:
        return f.read()


@tool
def append_long_term_memory(content: str, section: MemorySection) -> str:
    """Append one or more lines to a section of the long-term memory file.

    The memory file has three sections: words, phrases, sentence expressions.
    The new content is appended at the end of the chosen section,
    before the next section heading.

    Args:
        content: Line(s) to add, e.g. "chat - le chat (cat)".
        section: Target section — 'words', 'phrases', or 'expressions'.

    Returns:
        A confirmation message or an error description.
    """
    memory_file = os.environ.get("MEMORY_FILE")
    if not memory_file:
        return "Error: MEMORY_FILE environment variable is not set."

    try:
        text = _ensure_file(memory_file)
        heading = SECTION_HEADINGS[section]

        # Find the heading and insert after it, before the next heading (or EOF)
        pattern = rf"({re.escape(heading)}\n)(.*?)(\n##|\Z)"
        entry = content if content.endswith("\n") else content + "\n"

        def replacer(m: re.Match) -> str:
            section_body = m.group(2)
            separator = "\n" if section_body and not section_body.endswith("\n") else ""
            return m.group(1) + section_body + separator + entry + m.group(3)

        updated, count = re.subn(pattern, replacer, text, count=1, flags=re.DOTALL)
        if count == 0:
            return f"Error: section heading '{heading}' not found in memory file."

        with open(memory_file, "w", encoding="utf-8") as f:
            f.write(updated)

        return f"Memory appended successfully (section: {section}) → {memory_file}"
    except OSError as e:
        return f"Error writing memory file: {e}"
