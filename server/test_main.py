import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app, ALLOWED_CONTENT_TYPES

client = TestClient(app)

FAKE_KEY = "some-uuid.png"


def post_image(content: bytes, content_type: str):
    return client.post(
        "/images",
        files={"file": ("test", io.BytesIO(content), content_type)},
    )


# ---------------------------------------------------------------------------
# Successful upload
# ---------------------------------------------------------------------------

class TestUploadSuccess:
    @pytest.mark.parametrize("content_type", sorted(ALLOWED_CONTENT_TYPES))
    def test_returns_201_for_allowed_types(self, content_type):
        with patch("main.upload_stream", return_value=FAKE_KEY):
            response = post_image(b"data", content_type)
        assert response.status_code == 201

    @pytest.mark.parametrize("content_type", sorted(ALLOWED_CONTENT_TYPES))
    def test_returns_key_for_allowed_types(self, content_type):
        with patch("main.upload_stream", return_value=FAKE_KEY):
            response = post_image(b"data", content_type)
        assert response.json() == {"key": FAKE_KEY}

    def test_stream_passed_to_upload(self):
        with patch("main.upload_stream", return_value=FAKE_KEY) as mock_upload:
            post_image(b"hello", "image/png")
        mock_upload.assert_called_once()
        _, call_content_type = mock_upload.call_args[0]
        assert call_content_type == "image/png"


# ---------------------------------------------------------------------------
# Unsupported media type
# ---------------------------------------------------------------------------

class TestUnsupportedMediaType:
    @pytest.mark.parametrize("content_type", [
        "application/pdf",
        "text/plain",
        "video/mp4",
        "application/octet-stream",
    ])
    def test_returns_415(self, content_type):
        response = post_image(b"data", content_type)
        assert response.status_code == 415

    def test_error_detail_contains_rejected_type(self):
        response = post_image(b"data", "application/pdf")
        assert "application/pdf" in response.json()["detail"]

    def test_upload_not_called_for_disallowed_type(self):
        with patch("main.upload_stream") as mock_upload:
            post_image(b"data", "text/plain")
        mock_upload.assert_not_called()


# ---------------------------------------------------------------------------
# Missing file
# ---------------------------------------------------------------------------

class TestMissingFile:
    def test_returns_422_when_no_file_provided(self):
        response = client.post("/images")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Upload error (misconfigured env)
# ---------------------------------------------------------------------------

class TestUploadError:
    def test_returns_500_on_value_error(self):
        with patch("main.upload_stream", side_effect=ValueError("MINIO_BUCKET not set")):
            response = post_image(b"data", "image/png")
        assert response.status_code == 500

    def test_error_detail_contains_message(self):
        with patch("main.upload_stream", side_effect=ValueError("MINIO_BUCKET not set")):
            response = post_image(b"data", "image/png")
        assert "MINIO_BUCKET not set" in response.json()["detail"]
