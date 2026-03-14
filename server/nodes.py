import os

import httpx
import ollama
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

    message_oid = ObjectId(state["message_id"])

    # Latest summary whose toId is less than the current message (ObjectIds are monotonically increasing)
    relevant = [s for s in summaries if s["toId"] < message_oid]
    start_id = max(s["toId"] for s in relevant) if relevant else None

    history: list[Message] = [
        {"id": str(m["_id"]), "role": m["role"], "content": m["content"]}
        for m in messages
        if (start_id is None or m["_id"] > start_id) and m["_id"] < message_oid
    ]

    return {**state, "message_history": history}


_ollama_client: ollama.Client | None = None


def _get_ollama_client() -> ollama.Client:
    global _ollama_client
    if _ollama_client is None:
        ollama_url = os.environ.get("OLLAMA_URL")
        if not ollama_url:
            raise ValueError("Missing required environment variable: OLLAMA_URL")
        _ollama_client = ollama.Client(host=ollama_url)
    return _ollama_client


def describe_images(state: ConversationState) -> ConversationState:
    ollama_model = os.environ.get("OLLAMA_OCR_MODEL")
    if not ollama_model:
        raise ValueError("Missing required environment variable: OLLAMA_OCR_MODEL")

    client = _get_ollama_client()
    descriptions: list[str] = []

    for url in state["request"]["image_urls"]:
        image_bytes = httpx.get(url).raise_for_status().content
        result = client.chat(
            model=ollama_model,
            messages=[{
                "role": "user",
                "content": "Describe this image in detail.",
                "images": [image_bytes],
            }],
        )
        descriptions.append(result.message.content)

    return {**state, "request": {**state["request"], "image_descriptions": descriptions}}


def assemble_prompt(state: ConversationState) -> ConversationState:
    system_content = (
        "You are a French learning assistant. "
        "Your goal is to help the user memorize French vocabulary, phrases, and sentence expressions.\n\n"
        "## How you interact\n"
        "- Primarily ask Chinese → French translation questions (CHN→FRE), occasionally French → Chinese (FRE→CHN).\n"
        "- Draw questions from the user's vocabulary list and from any content in the conversation "
        "(e.g. words or phrases extracted from image descriptions).\n"
        "- Invent related translation problems that reinforce and extend what the user already knows.\n"
        "- After the user answers, immediately tell them whether they are correct or not, "
        "provide the correct answer with a brief explanation if needed, then ask the next question.\n"
        "- Keep a encouraging, patient tone. One question at a time.\n\n"
        "## User's vocabulary (long-term memory)\n"
    )
    if state.get("long_term_memory"):
        system_content += state["long_term_memory"]
    else:
        system_content += "(empty — no vocabulary recorded yet)"

    messages = [{"role": "system", "content": system_content}]

    for m in state.get("message_history", []):
        messages.append({"role": m["role"], "content": m["content"]})

    request = state["request"]
    user_content = request["content"]
    for url, description in zip(request["image_urls"], request["image_descriptions"]):
        user_content += f"\n\n## Image ({url})\n{description}"

    messages.append({"role": "user", "content": user_content})

    return {**state, "prompt": messages}


def generate_response(state: ConversationState) -> ConversationState:
    ollama_model = os.environ.get("OLLAMA_MODEL")
    if not ollama_model:
        raise ValueError("Missing required environment variable: OLLAMA_MODEL")

    result = _get_ollama_client().chat(model=ollama_model, messages=state["prompt"])

    return {**state, "response": result.message.content}


def summarize_message_history(state: ConversationState) -> ConversationState:
    if not state["message_history"]:
        return state

    ollama_model = os.environ.get("OLLAMA_MODEL")
    if not ollama_model:
        raise ValueError("Missing required environment variable: OLLAMA_MODEL")

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in state["message_history"]
    )
    result = _get_ollama_client().chat(
        model=ollama_model,
        messages=[
            {"role": "system", "content": "Summarize the following conversation concisely."},
            {"role": "user", "content": history_text},
        ],
    )
    summary_text = result.message.content

    to_id = ObjectId(state["message_history"][-1]["id"])

    col = get_conversations()
    conversation_id = ObjectId(state["conversation_id"])

    result = col.update_one(
        {"_id": conversation_id, "summaries.toId": to_id},
        {"$set": {"summaries.$.text": summary_text}},
    )
    if result.matched_count == 0:
        col.update_one(
            {"_id": conversation_id},
            {"$push": {"summaries": {"toId": to_id, "text": summary_text}}},
        )

    return state
