from bson import ObjectId

from db_client import get_conversations
from state import ConversationState, Message


def load_message_history(state: ConversationState) -> ConversationState:
    conversation = get_conversations().find_one(
        {"_id": ObjectId(state["conversation_id"])},
        {"messages": 1, "summaries": 1},
    )
    if conversation is None:
        return {**state, "message_history": []}

    messages = conversation.get("messages", [])
    summaries = conversation.get("summaries", [])

    message_oid = ObjectId(state["message_id"])

    relevant = [s for s in summaries if s["toId"] < message_oid]
    start_id = max(s["toId"] for s in relevant) if relevant else None

    history: list[Message] = [
        {"id": str(m["_id"]), "role": m["role"], "content": m["content"]}
        for m in messages
        if (start_id is None or m["_id"] > start_id) and m["_id"] < message_oid
    ]

    return {**state, "message_history": history}
