from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from s3 import upload_stream_to_s3

app = FastAPI()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
}


class ImageUploadResponse(BaseModel):
    url: str


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
