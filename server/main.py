from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from db import get_conversations
from s3 import upload_stream_to_s3

app = FastAPI()

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


class ImageUploadResponse(BaseModel):
    url: str


@app.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation() -> ConversationResponse:
    try:
        result = get_conversations().insert_one({"messages": []})
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ConversationResponse(id=str(result.inserted_id))


class AddMessageResponse(BaseModel):
    assistant_message_id: str


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
                {"_id": ObjectId(), "role": "user", "content": body.message, "status": "processed"},
                {"_id": assistant_id, "role": "assistant", "content": "", "status": "pending"},
            ]}}},
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return AddMessageResponse(assistant_message_id=str(assistant_id))


@app.post("/images", response_model=ImageUploadResponse, status_code=201)
async def upload_image(file: UploadFile) -> ImageUploadResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type '{file.content_type}'. "
                   f"Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    try:
        url = upload_stream_to_s3(file.file, file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ImageUploadResponse(url=url)
