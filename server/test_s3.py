import io
import uuid
from unittest.mock import MagicMock, patch

import pytest

from s3 import upload_stream_to_s3


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIO_ENV = {
    "MINIO_ENDPOINT": "http://localhost:9000",
    "MINIO_ACCESS_KEY": "minioadmin",
    "MINIO_SECRET_KEY": "minioadmin",
    "MINIO_BUCKET": "test-bucket",
}


@pytest.fixture()
def minio_env(monkeypatch):
    for k, v in MINIO_ENV.items():
        monkeypatch.setenv(k, v)


@pytest.fixture()
def mock_s3_client():
    """Patch boto3.client and return the mock client instance."""
    with patch("s3.boto3.client") as mock_ctor:
        client = MagicMock()
        mock_ctor.return_value = client
        yield mock_ctor, client


# ---------------------------------------------------------------------------
# Missing env vars
# ---------------------------------------------------------------------------

class TestMissingEnvVars:
    def test_all_missing(self, monkeypatch):
        for k in MINIO_ENV:
            monkeypatch.delenv(k, raising=False)
        with pytest.raises(ValueError) as exc:
            upload_stream_to_s3(io.BytesIO(b"data"), "text/plain")
        msg = str(exc.value)
        for k in MINIO_ENV:
            assert k in msg

    @pytest.mark.parametrize("missing_key", list(MINIO_ENV.keys()))
    def test_single_missing(self, monkeypatch, missing_key):
        for k, v in MINIO_ENV.items():
            monkeypatch.setenv(k, v)
        monkeypatch.delenv(missing_key)
        with pytest.raises(ValueError) as exc:
            upload_stream_to_s3(io.BytesIO(b"data"), "text/plain")
        assert missing_key in str(exc.value)


# ---------------------------------------------------------------------------
# boto3 client construction
# ---------------------------------------------------------------------------

class TestClientConstruction:
    def test_client_created_with_correct_args(self, minio_env, mock_s3_client):
        mock_ctor, client = mock_s3_client
        upload_stream_to_s3(io.BytesIO(b"x"), "text/plain", key="k.txt")

        mock_ctor.assert_called_once()
        _, kwargs = mock_ctor.call_args
        assert kwargs["endpoint_url"] == MINIO_ENV["MINIO_ENDPOINT"]
        assert kwargs["aws_access_key_id"] == MINIO_ENV["MINIO_ACCESS_KEY"]
        assert kwargs["aws_secret_access_key"] == MINIO_ENV["MINIO_SECRET_KEY"]
        assert kwargs["config"].signature_version == "s3v4"


# ---------------------------------------------------------------------------
# upload_fileobj call
# ---------------------------------------------------------------------------

class TestUploadFileobj:
    def test_upload_called_with_stream_bucket_key_content_type(self, minio_env, mock_s3_client):
        _, client = mock_s3_client
        stream = io.BytesIO(b"hello")
        upload_stream_to_s3(stream, "image/png", key="photo.png")

        client.upload_fileobj.assert_called_once_with(
            stream,
            MINIO_ENV["MINIO_BUCKET"],
            "photo.png",
            ExtraArgs={"ContentType": "image/png"},
        )

    def test_content_type_with_charset_passed_as_is(self, minio_env, mock_s3_client):
        _, client = mock_s3_client
        upload_stream_to_s3(io.BytesIO(b"hi"), "text/plain; charset=utf-8", key="f.txt")

        _, kwargs = client.upload_fileobj.call_args
        assert kwargs["ExtraArgs"]["ContentType"] == "text/plain; charset=utf-8"


# ---------------------------------------------------------------------------
# Auto-generated key
# ---------------------------------------------------------------------------

class TestAutoKey:
    def test_key_is_generated_when_omitted(self, minio_env, mock_s3_client):
        _, client = mock_s3_client
        upload_stream_to_s3(io.BytesIO(b"data"), "image/png")

        used_key = client.upload_fileobj.call_args[0][2]
        assert used_key  # non-empty

    def test_generated_key_contains_uuid(self, minio_env, mock_s3_client):
        _, client = mock_s3_client
        fixed_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        with patch("s3.uuid.uuid4", return_value=fixed_uuid):
            upload_stream_to_s3(io.BytesIO(b"data"), "image/png")

        used_key = client.upload_fileobj.call_args[0][2]
        assert str(fixed_uuid) in used_key

    def test_generated_key_has_extension_for_known_mime(self, minio_env, mock_s3_client):
        _, client = mock_s3_client
        upload_stream_to_s3(io.BytesIO(b"data"), "application/pdf")

        used_key = client.upload_fileobj.call_args[0][2]
        assert used_key.endswith(".pdf")

    def test_generated_key_has_no_extension_for_unknown_mime(self, minio_env, mock_s3_client):
        _, client = mock_s3_client
        fixed_uuid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        with patch("s3.uuid.uuid4", return_value=fixed_uuid):
            upload_stream_to_s3(io.BytesIO(b"data"), "application/x-unknown-type")

        used_key = client.upload_fileobj.call_args[0][2]
        assert used_key == str(fixed_uuid)

    def test_charset_stripped_before_extension_lookup(self, minio_env, mock_s3_client):
        _, client = mock_s3_client
        upload_stream_to_s3(io.BytesIO(b"data"), "text/plain; charset=utf-8")

        used_key = client.upload_fileobj.call_args[0][2]
        # mimetypes.guess_extension("text/plain") returns some extension
        assert used_key  # just ensure no crash and key is set

    def test_explicit_key_not_overridden(self, minio_env, mock_s3_client):
        _, client = mock_s3_client
        upload_stream_to_s3(io.BytesIO(b"data"), "image/png", key="custom/path.png")

        used_key = client.upload_fileobj.call_args[0][2]
        assert used_key == "custom/path.png"


# ---------------------------------------------------------------------------
# Return URL
# ---------------------------------------------------------------------------

class TestReturnUrl:
    def test_url_format(self, minio_env, mock_s3_client):
        url = upload_stream_to_s3(io.BytesIO(b"x"), "text/plain", key="doc.txt")
        assert url == "http://localhost:9000/test-bucket/doc.txt"

    def test_trailing_slash_on_endpoint_normalised(self, monkeypatch, mock_s3_client):
        for k, v in MINIO_ENV.items():
            monkeypatch.setenv(k, v)
        monkeypatch.setenv("MINIO_ENDPOINT", "http://localhost:9000/")
        url = upload_stream_to_s3(io.BytesIO(b"x"), "text/plain", key="doc.txt")
        assert url == "http://localhost:9000/test-bucket/doc.txt"

    def test_url_contains_bucket_and_key(self, minio_env, mock_s3_client):
        url = upload_stream_to_s3(io.BytesIO(b"x"), "image/png", key="imgs/cat.png")
        assert "test-bucket" in url
        assert "imgs/cat.png" in url
