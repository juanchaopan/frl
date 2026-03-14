import mimetypes
import os
import uuid
from typing import BinaryIO

import boto3
from botocore.client import Config


def upload_stream_to_s3(
    stream: BinaryIO,
    content_type: str,
    key: str | None = None,
) -> str:
    """Upload a binary stream to a MinIO bucket and return its URL.

    Env vars:
        MINIO_ENDPOINT   - MinIO server URL, e.g. "http://localhost:9000" (required)
        MINIO_ACCESS_KEY - access key (required)
        MINIO_SECRET_KEY - secret key (required)
        MINIO_BUCKET     - target bucket name (required)

    Args:
        stream:       Readable binary stream (file object, BytesIO, …).
        content_type: MIME type of the object, e.g. "image/png".
        key:          Object key. A random UUID-based key is generated when omitted.

    Returns:
        URL of the uploaded object (<endpoint>/<bucket>/<key>).

    Raises:
        ValueError: If any required env var is missing.
        botocore.exceptions.BotoCoreError / ClientError: on MinIO/S3 failures.
    """
    endpoint = os.environ.get("MINIO_ENDPOINT")
    access_key = os.environ.get("MINIO_ACCESS_KEY")
    secret_key = os.environ.get("MINIO_SECRET_KEY")
    bucket = os.environ.get("MINIO_BUCKET")

    missing = [n for n, v in {
        "MINIO_ENDPOINT": endpoint,
        "MINIO_ACCESS_KEY": access_key,
        "MINIO_SECRET_KEY": secret_key,
        "MINIO_BUCKET": bucket,
    }.items() if not v]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    if key is None:
        mime_base = content_type.split(";")[0].strip()
        ext = mimetypes.guess_extension(mime_base) or ""
        key = f"{uuid.uuid4()}{ext}"

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )

    s3.upload_fileobj(
        stream,
        bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )

    return f"{endpoint.rstrip('/')}/{bucket}/{key}"
