import os
from enum import Enum
from langchain_core.tools import tool


class MemoryUpdateMode(str, Enum):
    append = "append"
    replace = "replace"


@tool
def update_long_term_memory(content: str, mode: MemoryUpdateMode = MemoryUpdateMode.append) -> str:
    """Update the long-term memory markdown file.

    Args:
        content: The markdown content to write. In 'append' mode this is added
                 to the end of the existing file. In 'replace' mode the entire
                 file is overwritten with this content.
        mode: 'append' (default) adds content to the end of the file;
              'replace' overwrites the file completely.

    Returns:
        A confirmation message indicating success or an error description.
    """
    memory_file = os.environ.get("MEMORY_FILE")
    if not memory_file:
        return "Error: MEMORY_FILE environment variable is not set."

    try:
        if mode == MemoryUpdateMode.replace:
            with open(memory_file, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            # Append: add a newline separator if the file already has content
            existing = ""
            if os.path.exists(memory_file):
                with open(memory_file, "r", encoding="utf-8") as f:
                    existing = f.read()

            with open(memory_file, "w", encoding="utf-8") as f:
                if existing and not existing.endswith("\n"):
                    f.write(existing + "\n" + content)
                elif existing:
                    f.write(existing + content)
                else:
                    f.write(content)

        return f"Memory updated successfully ({mode} mode) → {memory_file}"
    except OSError as e:
        return f"Error writing memory file: {e}"
