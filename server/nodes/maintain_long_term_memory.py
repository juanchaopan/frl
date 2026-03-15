import os

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from state import ConversationState
from tools import append_long_term_memory

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        url = os.environ.get("OLLAMA_URL")
        model = os.environ.get("OLLAMA_MODEL")
        if not url or not model:
            raise ValueError("Missing required environment variables: OLLAMA_URL, OLLAMA_MODEL")
        _agent = create_agent(
            model=ChatOllama(base_url=url, model=model),
            tools=[append_long_term_memory],
        )
    return _agent


def maintain_long_term_memory(state: ConversationState) -> ConversationState:
    request = state["request"]
    user_content = request["content"]
    for key, description in zip(request["image_keys"], request["image_descriptions"]):
        user_content += f"\n\n## Image ({key})\n{description}"

    long_term_memory = state.get("long_term_memory") or "(empty)"

    _get_agent().invoke({"messages": [
        SystemMessage(content=(
            "You are a French vocabulary extractor.\n\n"
            "You will be given the user's current vocabulary and a new piece of content. "
            "Extract every French word, phrase, or sentence expression that appears in the content "
            "and is NOT already in the vocabulary. "
            "For each new item, call the append_long_term_memory tool with the item formatted as "
            "'FRE - CHN' (French term followed by its Chinese translation) "
            "and the appropriate section: 'words', 'phrases', or 'expressions'.\n\n"
            "## Current vocabulary\n"
            f"{long_term_memory}"
        )),
        HumanMessage(content=user_content),
    ]})

    return {}
