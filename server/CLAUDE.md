# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Python 3.11, managed with **Poetry** (venv at `.venv/`)
- Interpreter: `.venv/bin/python`

## Commands

```bash
# Install dependencies
poetry install

# Run all tests
.venv/bin/pytest -v

# Run a single test file
.venv/bin/pytest test_main.py -v

# Run a single test
.venv/bin/pytest test_main.py::TestUploadSuccess::test_returns_201_for_allowed_types -v

# Start the API server
.venv/bin/uvicorn main:app --reload
```

## Architecture

The project is a FastAPI server with a LangGraph/LangChain agent layer and MinIO-backed file storage.

### File overview

| File | Purpose |
|---|---|
| `main.py` | FastAPI app — currently exposes `POST /images` |
| `s3.py` | MinIO upload via boto3 — `upload_stream_to_s3(stream, content_type, key?)` returns a URL |
| `tools.py` | LangChain `@tool` — `update_long_term_memory(content, mode)` for agent long-term memory |

### S3 / MinIO client

`s3.py` holds a module-level singleton (`_s3_client`). `_get_s3_client()` initialises it lazily on first call using env vars `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`. `MINIO_BUCKET` is read per-call inside `upload_stream_to_s3`. Tests reset `s3._s3_client = None` in an autouse fixture to avoid singleton bleed between tests.

### Agent memory tool

`tools.py` exposes a single LangChain tool that reads/writes a markdown file at `$MEMORY_FILE`. It supports `append` (default) and `replace` modes.

### Required environment variables

| Variable | Used by |
|---|---|
| `MINIO_ENDPOINT` | `s3._get_s3_client()` |
| `MINIO_ACCESS_KEY` | `s3._get_s3_client()` |
| `MINIO_SECRET_KEY` | `s3._get_s3_client()` |
| `MINIO_BUCKET` | `s3.upload_stream_to_s3()` |
| `MEMORY_FILE` | `tools.update_long_term_memory` |
| `OLLAMA_URL` | `nodes._get_ollama_client()` |
| `OLLAMA_MODEL` | `nodes.summarize_message_history`, `nodes.generate_response` |
| `OLLAMA_OCR_MODEL` | `nodes.describe_images` (vision/OCR model e.g. llava) |

### MongoDB conversation schema

Every conversation document must be initialised as `{"messages": [], "summaries": []}`.

```json
{
  "_id": "ObjectId",
  "messages": [
    {
      "_id": "ObjectId",
      "role": "user | assistant",
      "content": "str",
      "images": [{ "url": "str", "description": "str" }],
      "status": "processed | pending"
    }
  ],
  "summaries": [
    {
      "toId": "ObjectId",
      "text": "str"
    }
  ]
}
```

`summaries` allows the agent to compress older message history. `toId` is the `_id` of the last message the summary covers. Since MongoDB ObjectIds are monotonically increasing, they are compared directly (no array index needed) to determine which messages fall before or after a summary.

### Testing approach

- All S3 and MinIO calls are mocked — no real server needed for unit tests.
- `test_main.py` patches `main.upload_stream_to_s3` using `fastapi.testclient.TestClient`.
- `test_s3.py` patches `s3._get_s3_client` for upload tests; patches `s3.boto3.client` for singleton construction tests.
- `test_tools.py` uses `tmp_path` and `monkeypatch.setenv` for full isolation.
