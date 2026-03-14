import os

from langchain.agents import create_agent
from langchain_ollama import ChatOllama

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


def generate_response(state: ConversationState) -> ConversationState:
    result = _get_agent().invoke({"messages": state["prompt"]})
    return {**state, "response": result["messages"][-1].content}
