# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
poetry install
.venv/bin/pytest -v                                      # all tests
.venv/bin/pytest test_main.py::ClassName::test_name -v   # single test
.venv/bin/uvicorn main:app --host 0.0.0.0 --reload       # dev server
```

## Project overview

A French-language learning assistant. Users send messages (text + images); the server runs a LangGraph pipeline that describes images, retrieves context, generates a teaching response, and streams it token-by-token to clients via Redis.

## REST API

| Method | Path | Description |
|---|---|---|
| `POST` | `/conversations` | Create empty conversation |
| `POST` | `/conversations/{id}/messages` | Add user message → returns `assistant_message_id`, triggers graph |
| `GET` | `/conversations/{id}/messages?from_message_id=` | SSE stream of messages from given ID |
| `POST` | `/images` | Upload image to MinIO → returns key |

### `POST /conversations/{id}/messages` request
```json
{ "message": "str", "image_keys": ["key", ...] }
```

### `GET /conversations/{id}/messages` SSE format
Every event is `data: {"type": "content"|"end", "content": "str"}`.
- Processed messages: one `content` event then one `end` event.
- Pending messages: one `content` event per token then `end`.
- Multiple users can consume the same stream independently — each connection uses `XREAD` from `0-0` (no consumer groups).

## LangGraph workflow (`graph.py`)

```
START
  → load_long_term_memory
  → describe_images
  → load_message_history        ←──────────────────┐
  → assemble_prompt                                  │
  → [token check: TIKTOKEN_ENCODING, MAX_CONTEXT_TOKENS]
       over limit  → summarize_message_history ──────┘
       within limit → generate_response → update_message → END
                    → maintain_long_term_memory          → END
```

`generate_response` and `maintain_long_term_memory` run in parallel.

## Node files (`nodes/`)

| File | LLM | Description |
|---|---|---|
| `load_long_term_memory.py` | — | Reads `MEMORY_FILE` into state |
| `load_message_history.py` | — | Fetches messages between latest summary `toId` and `message_id` |
| `describe_images.py` | `OLLAMA_OCR_MODEL` | Downloads images, base64-encodes, asks OCR model to describe |
| `assemble_prompt.py` | — | Builds `state.prompt` list from system instructions + history + request |
| `generate_response.py` | `OLLAMA_MODEL` | Calls LLM with assembled prompt |
| `update_message.py` | — | Writes `state.response` to MongoDB, sets status → `processed` |
| `summarize_message_history.py` | `OLLAMA_MODEL` | Summarises history, upserts into `summaries` by `toId` |
| `maintain_long_term_memory.py` | `OLLAMA_MODEL` + tools | Extracts new FRE-CHN vocabulary from request, appends to memory file |

Each LLM node owns a module-level `_agent` singleton built with `create_agent(ChatOllama(...))` from `langchain.agents`.

## Singleton pattern

All external clients (`boto3`, `MongoClient`, `Redis`, `ChatOllama` agents) are lazy module-level singletons initialised on first call. Env vars are validated at initialisation time, never at import time.

## MongoDB conversation schema

```json
{
  "_id": "ObjectId",
  "messages": [{
    "_id": "ObjectId",
    "role": "user | assistant",
    "content": "str",
    "images": [{ "key": "str", "description": "str" }],
    "status": "processed | pending"
  }],
  "summaries": [{
    "toId": "ObjectId",
    "text": "str"
  }]
}
```

`summaries.toId` is the `_id` of the last message covered. ObjectIds are monotonically increasing, so range queries use direct ObjectId comparison — no array indices needed.

`load_message_history` fetches messages where `toId < _id < message_id` (using the latest applicable summary as lower bound).

`summarize_message_history` upserts by `toId` (replace text if same `toId` exists, push otherwise) so users can re-trigger summarisation without duplicates.

## Long-term memory file (`MEMORY_FILE`)

Three `##` sections: `Words`, `Phrases`, `Sentence Expressions`. Tool `append_long_term_memory(content, section)` appends lines to the target section using regex. File is auto-created with empty sections if missing.

## Redis streaming

- **Write side** (`_run_graph`): XADD `{"type": "start"|"token"|"end", "content": "..."}` to key `stream:{message_id}`. Start entry + TTL (`REDIS_STREAM_TTL` seconds) written in the endpoint before the task fires.
- **Read side** (`_stream_pending_message`): XREAD from `0-0` with block timeout `REDIS_BLOCK_MS` ms. Each HTTP connection reads independently.

## Environment variables

| Variable | Used by |
|---|---|
| `MONGO_URI` | `db_client` |
| `MONGO_DB` | `db_client` |
| `MONGO_AUTH_SOURCE` | `db_client` — auth database (defaults to `MONGO_DB`, then `admin`) |
| `MONGO_DB_USERNAME` | `db_client` |
| `MONGO_DB_PASSWORD` | `db_client` |
| `MINIO_ENDPOINT` | `s3_client` |
| `MINIO_ACCESS_KEY` | `s3_client` |
| `MINIO_SECRET_KEY` | `s3_client` |
| `MINIO_BUCKET` | `s3_client` |
| `REDIS_URL` | `redis_client` |
| `REDIS_STREAM_TTL` | `main` — stream key expiry in seconds |
| `REDIS_BLOCK_MS` | `main` — XREAD block timeout in milliseconds |
| `OLLAMA_URL` | all LLM nodes |
| `OLLAMA_MODEL` | language model (summarise, generate, maintain memory) |
| `OLLAMA_OCR_MODEL` | vision model for image description (e.g. llava) |
| `MEMORY_FILE` | `tools`, `nodes/load_long_term_memory` |
| `TIKTOKEN_ENCODING` | `graph` — e.g. `cl100k_base` |
| `MAX_CONTEXT_TOKENS` | `graph` — token limit before summarisation |

## Testing

- `test_tools.py` — uses `tmp_path` + `monkeypatch.setenv`, no external deps.
- `test_s3.py` — patches `s3_client._get_client` and `s3_client.boto3.client`; autouse fixture resets `s3_client._client = None` between tests.
- `test_main.py` — patches `main.upload_stream` via `TestClient`.
