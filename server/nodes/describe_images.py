import base64
import os

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from s3_client import _get_client as _get_s3_client
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

    bucket = os.environ.get("MINIO_BUCKET")
    if not bucket:
        raise ValueError("Missing required environment variable: MINIO_BUCKET")

    for key in state["request"]["image_keys"]:
        obj = _get_s3_client().get_object(Bucket=bucket, Key=key)
        content = obj["Body"].read()
        mime = obj.get("ContentType", "image/jpeg").split(";")[0]
        b64 = base64.b64encode(content).decode()

        result = _get_agent().invoke({"messages": [
            HumanMessage(content=[
                {"type": "text", "text": "Describe this image in detail."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ])
        ]})
        descriptions.append(result["messages"][-1].content)

    return {"request": {**state["request"], "image_descriptions": descriptions}}
