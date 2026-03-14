import asyncio
import json
import os
from collections.abc import AsyncIterator

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from db_client import get_conversations
from graph import build_graph
from redis_client import get_redis
from s3_client import upload_stream

app = FastAPI()
_graph = build_graph()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
}


class ConversationResponse(BaseModel):
    id: str


class AddMessageRequest(BaseModel):
    message: str
    image_urls: list[str] = []


class AddMessageResponse(BaseModel):
    assistant_message_id: str


class ImageUploadResponse(BaseModel):
    url: str


async def _run_graph(conversation_id: str, message_id: str, image_urls: list[str], message: str) -> None:
    stream_key = f"stream:{message_id}"
    redis = await get_redis()
    try:
        initial_state = {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "request": {
                "content": message,
                "image_urls": image_urls,
                "image_descriptions": [],
            },
        }
        async for chunk, metadata in _graph.astream(initial_state, stream_mode="messages"):
            if metadata.get("langgraph_node") == "generate_response":
                content = chunk.content if hasattr(chunk, "content") else ""
                if content:
                    await redis.xadd(stream_key, {"type": "token", "content": content})
    finally:
        await redis.xadd(stream_key, {"type": "end"})


@app.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation() -> ConversationResponse:
    try:
        result = get_conversations().insert_one({"messages": [], "summaries": []})
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ConversationResponse(id=str(result.inserted_id))


@app.post("/conversations/{id}/messages", response_model=AddMessageResponse, status_code=201)
async def add_message(id: str, body: AddMessageRequest) -> AddMessageResponse:
    try:
        oid = ObjectId(id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Conversation not found")

    assistant_id = ObjectId()
    try:
        result = get_conversations().update_one(
            {"_id": oid},
            {"$push": {"messages": {"$each": [
                {"_id": ObjectId(), "role": "user", "content": body.message, "images": [{"url": url, "description": ""} for url in body.image_urls], "status": "processed"},
                {"_id": assistant_id, "role": "assistant", "content": "", "status": "pending"},
            ]}}},
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")

    ttl = os.environ.get("REDIS_STREAM_TTL")
    if not ttl:
        raise HTTPException(status_code=500, detail="Missing required environment variable: REDIS_STREAM_TTL")

    stream_key = f"stream:{assistant_id}"
    redis = await get_redis()
    await redis.xadd(stream_key, {"type": "start"})
    await redis.expire(stream_key, int(ttl))

    asyncio.create_task(_run_graph(id, str(assistant_id), body.image_urls, body.message))

    return AddMessageResponse(assistant_message_id=str(assistant_id))


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _stream_pending_message(message_id: str, block_ms: int) -> AsyncIterator[str]:
    """Read tokens from a Redis stream independently per connection using XREAD.

    Each caller tracks its own position from 0-0, so multiple concurrent
    readers receive all tokens without affecting each other — no consumer
    group is needed for fan-out delivery.
    """
    stream_key = f"stream:{message_id}"
    redis = await get_redis()
    last_id = "0-0"

    while True:
        entries = await redis.xread({stream_key: last_id}, block=block_ms, count=100)
        if not entries:
            break
        for _, records in entries:
            for entry_id, fields in records:
                last_id = entry_id
                entry_type = fields.get(b"type", b"").decode()
                if entry_type == "token":
                    yield _sse({"type": "content", "content": fields.get(b"content", b"").decode()})
                elif entry_type == "end":
                    yield _sse({"type": "end", "content": ""})
                    return


async def _generate_messages(conversation_id: str, from_message_id: str, block_ms: int) -> AsyncIterator[str]:
    from_oid = ObjectId(from_message_id)
    conversation = get_conversations().find_one(
        {"_id": ObjectId(conversation_id)},
        {"messages": 1},
    )
    if not conversation:
        return

    for message in conversation["messages"]:
        if message["_id"] < from_oid:
            continue
        if message["status"] == "processed":
            yield _sse({"type": "content", "content": message["content"]})
            yield _sse({"type": "end", "content": ""})
        else:
            async for event in _stream_pending_message(str(message["_id"]), block_ms):
                yield event


@app.get("/conversations/{id}/messages")
async def stream_messages(
    id: str,
    from_message_id: str = Query(...),
) -> StreamingResponse:
    try:
        ObjectId(id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        ObjectId(from_message_id)
    except InvalidId:
        raise HTTPException(status_code=422, detail="Invalid from_message_id")

    block_ms_str = os.environ.get("REDIS_BLOCK_MS")
    if not block_ms_str:
        raise HTTPException(status_code=500, detail="Missing required environment variable: REDIS_BLOCK_MS")

    return StreamingResponse(
        _generate_messages(id, from_message_id, int(block_ms_str)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/images", response_model=ImageUploadResponse, status_code=201)
async def upload_image(file: UploadFile) -> ImageUploadResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type '{file.content_type}'. "
                   f"Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    try:
        url = upload_stream(file.file, file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ImageUploadResponse(url=url)
