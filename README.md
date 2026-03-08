# ClearStreamAI - Compliance QA Pipeline

An AI-powered video compliance auditing system that analyzes YouTube videos against regulatory/brand rules and returns structured compliance findings.

This project combines:
- **Video intelligence** (Azure Video Indexer for transcript + OCR extraction)
- **RAG-based policy grounding** (Azure AI Search + embeddings)
- **LLM reasoning** (Azure OpenAI)
- **Workflow orchestration** (LangGraph)
- **Production API surface** (FastAPI)
- **Observability & Telemetry** (Azure Monitor OpenTelemetry)

---

## Why this project exists

Compliance reviews for video ads and marketing assets are often manual, slow, and inconsistent.  
This pipeline automates first-pass compliance checks by:

1. Ingesting a video URL
2. Extracting spoken and on-screen content
3. Retrieving relevant regulatory rules
4. Producing a machine-readable compliance verdict (`PASS`/`FAIL`) and issue list

---

## What it does

- Accepts a YouTube video URL
- Downloads and uploads the video to Azure Video Indexer
- Waits for indexing completion and extracts:
  - transcript
  - OCR text
  - basic metadata
- Queries Azure AI Search for related compliance rules
- Runs an Azure OpenAI compliance audit prompt
- Returns structured output:
  - `final_status`
  - `final_report`
  - `compliance_results[]`

---

## High-level architecture

### 1) Graph workflow (`LangGraph`)
- `index_video` node: video ingestion + indexing
- `audit_content` node: RAG retrieval + LLM compliance analysis

### 2) State contract
- Shared typed state (`VideoAuditState`) is passed between nodes
- Aggregated fields like `errors` and `compliance_results` are merged across node outputs

### 3) Interfaces
- **CLI runner** for local simulation (`main.py`)
- **FastAPI service** for application integration (`backend/src/api/server.py`)

### 4) Telemetry
- Optional Azure Monitor OpenTelemetry setup (`backend/src/api/telemetry.py`)

---

## Repository structure

```text
ComplianceQAPipeline/
├── backend/
│   ├── scripts/
│   │   └── index_documents.py        # PDF -> chunks -> Azure AI Search
│   └── src/
│       ├── api/
│       │   ├── server.py             # FastAPI endpoints (/audit, /health)
│       │   └── telemetry.py          # Azure Monitor telemetry bootstrap
│       ├── graph/
│       │   ├── workflow.py           # LangGraph topology
│       │   ├── nodes.py              # Graph node implementations
│       │   └── state.py              # Shared graph state schema
│       └── services/
│           └── video_indexer.py      # Azure Video Indexer integration
├── main.py                           # CLI execution entrypoint
├── requirements.txt                  # pip-compatible dependencies
├── pyproject.toml                    # project metadata + dependencies
└── vercel.json                       # Vercel deployment config
```

---

## Tech stack

- Python 3.12+
- FastAPI
- LangChain + LangGraph
- Azure OpenAI
- Azure AI Search
- Azure Video Indexer
- Azure Monitor OpenTelemetry

---

## Local setup

## 1) Prerequisites

- Python `>=3.12`
- Azure services configured:
  - Azure OpenAI
  - Azure AI Search
  - Azure Video Indexer
- Azure authentication available locally (`az login`) or service principal env credentials

## 2) Install dependencies

Using `uv` (recommended):

```bash
uv sync
```

or using `pip`:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Configure environment variables

Create a `.env` in project root with values for:

```env
# --- AZURE STORAGE ---
AZURE_STORAGE_CONNECTION_STRING=""

# --- AZURE OPENAI ---
AZURE_OPENAI_API_KEY=""
AZURE_OPENAI_ENDPOINT="https://<your-resource-name>[.cognitiveservices.azure.com/](https://.cognitiveservices.azure.com/)"
AZURE_OPENAI_API_VERSION="2024-12-01-preview"
AZURE_OPENAI_CHAT_DEPLOYMENT="gpt-4o"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT="text-embedding-3-small"

# --- AZURE AI SEARCH (The Knowledge Base) ---
AZURE_SEARCH_ENDPOINT="https://<your-search-name>.search.windows.net"
AZURE_SEARCH_API_KEY=""
AZURE_SEARCH_INDEX_NAME="compliance-rules-index"

# --- AZURE VIDEO INDEXER (Identity Auth) ---
AZURE_VI_NAME="clearstreamai"
AZURE_VI_LOCATION="eastus"
AZURE_VI_ACCOUNT_ID=""
AZURE_SUBSCRIPTION_ID=""
AZURE_RESOURCE_GROUP="ClearStreamAI"
AZURE_TENANT_ID=""

# --- OBSERVABILITY (Azure Monitor) ---
APPLICATIONINSIGHTS_CONNECTION_STRING=""

# --- LANGSMITH (Tracing) ---
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_ENDPOINT="[https://api.smith.langchain.com](https://api.smith.langchain.com)"
LANGCHAIN_API_KEY=""
LANGCHAIN_PROJECT="clear-stream-prod"
```

> If using Azure CLI authentication, run `az login` and set the correct subscription.

---

## Index knowledge base documents (RAG setup)

Put compliance PDFs in `backend/data/`, then run:

```bash
uv run python backend/scripts/index_documents.py
```

This script:
- loads PDFs
- chunks content
- embeds chunks with Azure OpenAI
- uploads vectors to Azure AI Search

---

## Run the project locally

## Option A: CLI workflow run

```bash
uv run python main.py
```

This executes the full graph and prints a compliance report to terminal.

## Option B: FastAPI server

```bash
uv run uvicorn backend.src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

Audit request:

```bash
curl -X POST http://localhost:8000/audit \
  -H "Content-Type: application/json" \
  -d "{\"video_url\":\"https://youtu.be/your_video_id\"}"
```

---

## API contract

### `POST /audit`

Request:

```json
{
  "video_url": "https://youtu.be/your_video_id"
}
```

Response:

```json
{
  "session_id": "uuid",
  "video_id": "vid_xxxxxxxx",
  "status": "PASS | FAIL",
  "final_report": "Summary text",
  "compliance_results": [
    {
      "category": "Claim Validation",
      "severity": "CRITICAL",
      "description": "Issue explanation"
    }
  ]
}
```

### `GET /health`

Returns service liveness information.

---