from bson import ObjectId

from db_client import get_conversations
from state import ConversationState


def update_message(state: ConversationState) -> ConversationState:
    get_conversations().update_one(
        {"_id": ObjectId(state["conversation_id"]), "messages._id": ObjectId(state["message_id"])},
        {"$set": {"messages.$.content": state["response"], "messages.$.status": "processed"}},
    )
    return state
