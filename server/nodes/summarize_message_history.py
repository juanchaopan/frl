import os

from bson import ObjectId
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from db_client import get_conversations
from state import ConversationState

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        url = os.environ.get("OLLAMA_URL")
        model = os.environ.get("OLLAMA_MODEL")
        if not url or not model:
            raise ValueError("Missing required environment variables: OLLAMA_URL, OLLAMA_MODEL")
        _agent = create_agent(model=ChatOllama(base_url=url, model=model))
    return _agent


def summarize_message_history(state: ConversationState) -> ConversationState:
    if not state["message_history"]:
        return {}

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in state["message_history"]
    )

    result = _get_agent().invoke({"messages": [
        SystemMessage(content="Summarize the following conversation concisely."),
        HumanMessage(content=history_text),
    ]})
    summary_text = result["messages"][-1].content

    to_id = ObjectId(state["message_history"][-1]["id"])
    col = get_conversations()
    conversation_id = ObjectId(state["conversation_id"])

    db_result = col.update_one(
        {"_id": conversation_id, "summaries.toId": to_id},
        {"$set": {"summaries.$.text": summary_text}},
    )
    if db_result.matched_count == 0:
        col.update_one(
            {"_id": conversation_id},
            {"$push": {"summaries": {"toId": to_id, "text": summary_text}}},
        )

    return {}
