# Architecture Overview (ARB Brief)

## Scope and Purpose
- End-to-end invoice ingestion, extraction, validation, HITL review, and persistence.
- Components: FastAPI services, Azure Document Intelligence, optional LLM fallback (Azure OpenAI text-based and multimodal), SQL persistence (Azure SQL), Streamlit HITL UI, Azure Blob for raw PDFs.
- Supports both text-based and scanned/image-based PDFs with multimodal LLM fallback.

## High-Level Flow
1) Upload/select PDF (API or Streamlit) → PDF validated (reject encrypted early; scanned allowed).  
2) Azure Document Intelligence extracts all 53 canonical fields with field-level confidence scores.  
3) `FieldExtractor` maps DI output to canonical `Invoice` (prioritizes DI totals/POs, merges PST/QST, acceptance %, defaults confidences).  
4) Low-confidence fields → intelligent LLM fallback:
   - **Scanned PDFs**: Detected automatically; multimodal LLM fallback with rendered PDF page images (PNG/JPEG, cached, configurable page selection)
   - **Text-based PDFs**: Text-based LLM fallback with OCR snippet
   - Fields grouped (header, addresses, Canadian taxes, line items) for efficient processing
   - Minimal, sanitized payload + OCR snippet + images (for multimodal)
   - TTL cache with LRU eviction for LLM responses and rendered images
   - Async execution with exponential backoff; stop further groups on 429
5) Suggestions parsed/sanitized/validated; only applied if confidence improves; dynamic confidence scoring based on correction context; persistence via `DatabaseService` (SQLAlchemy).  
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
- **System prompt**: Corrections only for low-confidence fields; no invention; null when unsure; preserve totals/tax/currency; JSON-only output with defined formats (dates ISO, monetary numbers, address objects). Supports all 57 canonical fields.
- **Text-based LLM**: Minimal prompt payload with only low-confidence fields + sanitized DI subset + OCR snippet (beginning, middle, end sections for context).
- **Multimodal LLM**: Same prompt structure + rendered PDF page images (base64 PNG/JPEG) for scanned documents. Automatic scanned PDF detection. Image rendering optimized with caching, multiple formats, configurable page selection (first/last/middle/all), and quality control.
- **Robust sanitization**: Dates/decimals/nested SDK objects sanitized before LLM calls.
- **Response validation**: LLM suggestions validated (date formats, amount ranges, address structure) before application.
- **Non-JSON outputs**: Coerced when possible; otherwise logged and skipped.
- **Rate-limit resilience**: Async grouped calls with exponential backoff; halt remaining groups on 429; TTL cache with LRU eviction for suggestions (by file+fields+snapshot) and rendered images.
- **Dynamic confidence**: Confidence scores calculated based on correction context (filled blank vs corrected wrong value vs confirmed existing).

## Persistence and Data Model
- Azure SQL via SQLAlchemy/AsyncSession.  
- Canonical schema in `schemas/invoice.canonical.v1.schema.json`; HITL view in `schemas/invoice.hitl_view.v1.schema.json`.  
- **53 canonical fields** extractable from Document Intelligence (all fields with DI mappings).
- DI field mapping isolated in `FieldExtractor`; totals/POs prefer DI native values; line-item tax handling merges PST/QST, derives combined tax, applies acceptance %.
- Field-level confidence scores tracked for all extracted fields.

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
- **Unit tests**: `field_extractor` mapping/line-item logic, JSON sanitizer/prompt builder in `extraction_service`, safe decimal parsing in HITL routes. Canonical field coverage tests for DI (53 fields), text-based LLM (57 fields), and multimodal LLM (57 fields).
- **Contract/schema**: Canonical and HITL JSON schemas (`schemas/invoice.*`) validated in tests.
- **Integration tests (API-level)**: FastAPI route tests (ingestion/hitl) with DI mocked; DB health endpoint; blob listing/extract endpoints.
- **Real service integration tests**: 
  - Real DI extraction tests (`test_real_di_extraction.py`) with isolated test databases
  - Real LLM extraction tests (`test_real_llm_extraction.py`) with full pipeline validation
  - Real multimodal LLM extraction tests (`test_real_multimodal_llm_extraction.py`) with scanned PDF detection and image rendering
  - LLM error handling tests (`test_llm_error_handling.py`) covering API failures, rate limiting, network issues
  - Multimodal LLM error handling tests (`test_multimodal_llm_error_handling.py`) covering image rendering failures and API errors
- **E2E/manual**: Streamlit + API happy path; upload/ingest/extract/review/save flows.
- **Resilience checks**: LLM fallback grouping/backoff, 429 handling, offline queue for saves (UI), partial success handling, retry logic with exponential backoff.
- **Documentation**: LLM behavior documented (`LLM_BEHAVIOR_DOCUMENTATION.md`), multimodal LLM behavior documented (`MULTIMODAL_LLM_BEHAVIOR_DOCUMENTATION.md`), DI mapping verification (`DI_MAPPING_VERIFICATION_REPORT.md`).

Gaps to consider: Multimodal LLM performance tests (image rendering performance, response times, large PDF handling); load/perf tests for large PDFs/line-items; authZ/authN coverage; automated UI regression; chaos/backoff tuning for sustained 429s.

## Open/Optional Decisions
- ✅ Exponential backoff implemented for LLM API calls (429 and other retryable errors).
- Circuit-breaker for repeated 429s (not yet implemented).
- Formal SLIs/SLOs for latency and fallback success.  
- AuthN/Z hardening for APIs and Streamlit (not covered here).
- Multimodal LLM performance testing and optimization (image rendering performance, response times, large PDF handling).

