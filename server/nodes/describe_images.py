import base64
import os

import httpx
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from state import ConversationState

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        url = os.environ.get("OLLAMA_URL")
        model = os.environ.get("OLLAMA_OCR_MODEL")
        if not url or not model:
            raise ValueError("Missing required environment variables: OLLAMA_URL, OLLAMA_OCR_MODEL")
        _agent = create_agent(model=ChatOllama(base_url=url, model=model))
    return _agent


def describe_images(state: ConversationState) -> ConversationState:
    descriptions: list[str] = []

    for url in state["request"]["image_urls"]:
        response = httpx.get(url)
        response.raise_for_status()
        mime = response.headers.get("content-type", "image/jpeg").split(";")[0]
        b64 = base64.b64encode(response.content).decode()

        result = _get_agent().invoke({"messages": [
            HumanMessage(content=[
                {"type": "text", "text": "Describe this image in detail."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ])
        ]})
        descriptions.append(result["messages"][-1].content)

    return {**state, "request": {**state["request"], "image_descriptions": descriptions}}
