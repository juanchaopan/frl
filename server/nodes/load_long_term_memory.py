import os

from state import ConversationState


def load_long_term_memory(state: ConversationState) -> ConversationState:
    memory_file = os.environ.get("MEMORY_FILE")
    if memory_file and os.path.exists(memory_file):
        with open(memory_file, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = ""
    return {**state, "long_term_memory": content}
