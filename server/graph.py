import os

import tiktoken
from langgraph.graph import END, START, StateGraph

from nodes import (
    assemble_prompt,
    describe_images,
    generate_response,
    load_long_term_memory,
    load_message_history,
    maintain_long_term_memory,
    summarize_message_history,
    update_message,
)
from state import ConversationState

def _get_encoding() -> tiktoken.Encoding:
    encoding_name = os.environ.get("TIKTOKEN_ENCODING")
    if not encoding_name:
        raise ValueError("Missing required environment variable: TIKTOKEN_ENCODING")
    return tiktoken.get_encoding(encoding_name)


def _count_prompt_tokens(state: ConversationState) -> int:
    encoding = _get_encoding()
    return sum(
        len(encoding.encode(m["content"]))
        for m in state["prompt"]
        if isinstance(m.get("content"), str)
    )


def _route_after_prompt(state: ConversationState) -> str | list[str]:
    max_tokens_str = os.environ.get("MAX_CONTEXT_TOKENS")
    if not max_tokens_str:
        raise ValueError("Missing required environment variable: MAX_CONTEXT_TOKENS")
    if _count_prompt_tokens(state) > int(max_tokens_str):
        return "summarize_message_history"
    return ["generate_response", "maintain_long_term_memory"]


def build_graph():
    graph = StateGraph(ConversationState)

    graph.add_node("load_long_term_memory", load_long_term_memory)
    graph.add_node("describe_images", describe_images)
    graph.add_node("load_message_history", load_message_history)
    graph.add_node("assemble_prompt", assemble_prompt)
    graph.add_node("summarize_message_history", summarize_message_history)
    graph.add_node("generate_response", generate_response)
    graph.add_node("update_message", update_message)
    graph.add_node("maintain_long_term_memory", maintain_long_term_memory)

    graph.add_edge(START, "load_long_term_memory")
    graph.add_edge("load_long_term_memory", "describe_images")
    graph.add_edge("describe_images", "load_message_history")
    graph.add_edge("load_message_history", "assemble_prompt")
    graph.add_conditional_edges("assemble_prompt", _route_after_prompt)
    graph.add_edge("summarize_message_history", "load_message_history")
    graph.add_edge("generate_response", "update_message")
    graph.add_edge("update_message", END)
    graph.add_edge("maintain_long_term_memory", END)

    return graph.compile()
