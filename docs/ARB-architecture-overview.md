# Architecture Overview (ARB Brief)

## Scope and Purpose
- End-to-end invoice ingestion, extraction, validation, HITL review, and persistence.
- Components: FastAPI services, Azure Document Intelligence, optional LLM fallback (Azure OpenAI), SQL persistence (Azure SQL), Streamlit HITL UI, Azure Blob for raw PDFs.

## High-Level Flow
1) Upload/select PDF (API or Streamlit) → PDF validated (reject encrypted early; scanned allowed).  
2) Azure Document Intelligence extracts fields.  
3) `FieldExtractor` maps DI output to canonical `Invoice` (prioritizes DI totals/POs, merges PST/QST, acceptance %, defaults confidences).  
4) Low-confidence fields → grouped LLM fallback (header, addresses, line items). Minimal, sanitized payload + OCR snippet. Caching + jitter between calls; stop further groups on 429.  
5) Suggestions parsed/sanitized; only applied if confidence improves; persistence via `DatabaseService` (SQLAlchemy).  
6) HITL UI fetches live data (no cache), shows LLM suggestions side-by-side; user edits and explicitly saves to DB. Offline queue retries on failure.

## Storage and Deployment (from vanilla architecture)
- Raw files: local storage by default (e.g., `./storage/raw/`); Azure Blob optional via config.
- Database: SQLite by default for dev; Azure SQL for production via `DATABASE_URL`.
- Deployment: local `uvicorn api.main:app --reload`; Docker Compose optional; Streamlit runs separately on 8501.
- Configuration via `.env` (Azure DI, Azure OpenAI, storage, DB).

## Key Components (code anchors)
- API entry: `api/main.py`
- Ingestion/health/blob: `api/routes/ingestion.py`
- HITL/suggestions/validation: `api/routes/hitl.py`
- Extraction pipeline: `src/extraction/extraction_service.py`, `src/extraction/field_extractor.py`, `src/ingestion/pdf_processor.py`
- Models/DB: `src/models/*`, `schemas/invoice.*.schema.json`
- UI: `streamlit_app.py`

## LLM Guardrails
- System prompt: corrections only for low-confidence fields; no invention; null when unsure; preserve totals/tax/currency; JSON-only output with defined formats (dates ISO, monetary numbers, address objects).  
- Minimal prompt payload: only low-confidence fields + sanitized DI subset + OCR snippet; robust sanitizer for dates/decimals/nested SDK objects.  
- Non-JSON outputs coerced when possible; otherwise logged and skipped.  
- Rate-limit resilience: grouped calls + jitter; halt remaining groups on 429; cache suggestions by file+fields+snapshot.

## Persistence and Data Model
- Azure SQL via SQLAlchemy/AsyncSession.  
- Canonical schema in `schemas/invoice.canonical.v1.schema.json`; HITL view in `schemas/invoice.hitl_view.v1.schema.json`.  
- DI field mapping isolated in `FieldExtractor`; totals/POs prefer DI native values; line-item tax handling merges PST/QST, derives combined tax, applies acceptance %.

## HITL UI (Streamlit)
- Fresh fetch (no cache) for invoice list/details.  
- Side-by-side LLM suggestions; explicit “Save to DB” and “Submit Validation”.  
- Live total metric updates with edits.  
- Offline queue for saves with retry; DB health check button; Azure Blob browser to trigger ingestion.

## Observability and Ops
- Logging around ingestion, LLM inputs/outputs/diffs, DB health.  
- Health endpoints: `/api/health/db` and `/api/ingestion/health/db`; blob listing and extraction triggers for ops.

## Security Notes
- Secrets in `.env`; Azure SQL connection string documented; firewall/driver steps required.  
- No secrets baked into code; archives containing `.env` should be handled carefully.

## Testing and Quality (Test Pyramid)
- Unit: `field_extractor` mapping/line-item logic, JSON sanitizer/prompt builder in `extraction_service`, safe decimal parsing in HITL routes.
- Contract/schema: canonical and HITL JSON schemas (`schemas/invoice.*`) validated in tests.
- Integration (API-level): FastAPI route tests (ingestion/hitl) with DI mocked; DB health endpoint; blob listing/extract endpoints.
- E2E/manual: Streamlit + API happy path; upload/ingest/extract/review/save flows.
- Resilience checks: LLM fallback grouping/jitter, 429 handling, offline queue for saves (UI).
Gaps to consider: load/perf tests for large PDFs/line-items; authZ/authN coverage; automated UI regression; chaos/backoff tuning for sustained 429s.

## Open/Optional Decisions
- Whether to add exponential backoff or circuit-breaker for repeated 429s.  
- Formal SLIs/SLOs for latency and fallback success.  
- AuthN/Z hardening for APIs and Streamlit (not covered here).

