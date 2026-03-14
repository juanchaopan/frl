import os

from bson import ObjectId

from db import get_conversations
from state import ConversationState, Message


def load_long_term_memory(state: ConversationState) -> ConversationState:
    memory_file = os.environ.get("MEMORY_FILE")
    if memory_file and os.path.exists(memory_file):
        with open(memory_file, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = ""
    return {**state, "long_term_memory": content}


def load_message_history(state: ConversationState) -> ConversationState:
    conversation = get_conversations().find_one(
        {"_id": ObjectId(state["conversation_id"])},
        {"messages": 1, "summaries": 1},
    )
    if conversation is None:
        return {**state, "message_history": []}

    messages = conversation.get("messages", [])
    summaries = conversation.get("summaries", [])

    # Find the index of the current message (exclusive upper bound)
    message_oid = ObjectId(state["message_id"])
    current_index = next(
        (i for i, m in enumerate(messages) if m["_id"] == message_oid),
        len(messages),
    )

    # Latest summary whose toIndex falls before the current message
    relevant = [s for s in summaries if s["toIndex"] < current_index]
    start_index = max(s["toIndex"] for s in relevant) + 1 if relevant else 0

    history: list[Message] = [
        {"role": m["role"], "content": m["content"]}
        for m in messages[start_index:current_index]
    ]

    return {**state, "message_history": history}
