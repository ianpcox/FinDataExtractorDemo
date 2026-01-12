# Architecture Overview (ARB Brief)

## Scope and Purpose
- End-to-end invoice ingestion, extraction, validation, HITL review, and persistence.
- Components: FastAPI services (33 routes across 9 modules), Azure Document Intelligence, optional LLM fallback (Azure OpenAI text-based and multimodal), SQL persistence (SQLite/Azure SQL), Streamlit HITL UI, Azure Blob Storage (optional).
- Supports both text-based and scanned/image-based PDFs with multimodal LLM fallback.
- Codebase: 9 major modules, ~27,000+ lines of Python code, 32 direct dependencies, 66 test files.
- Schema: 80 canonical fields with field-level confidence scores, 3 invoice subtypes (Standard, Shift Service, Per Diem Travel).

## High-Level Flow
1) **Ingestion**: Upload/select PDF (API or Streamlit) → PDF validated (reject encrypted early; scanned allowed) → Azure Blob Storage (optional) or local storage.  
2) **Extraction**: Azure Document Intelligence extracts **all 80 canonical fields** with field-level confidence scores. Invoice subtype detection (Standard, Shift Service, Per Diem Travel) for subtype-specific field extraction.  
3) **Field Mapping**: `FieldExtractor` maps DI output to canonical `Invoice` model (prioritizes DI totals/POs, merges PST/QST, applies acceptance %, defaults confidences).  
4) **LLM Fallback**: Low-confidence fields → intelligent LLM fallback:
   - **Scanned PDFs**: Detected automatically; multimodal LLM fallback with rendered PDF page images (PNG/JPEG, cached, configurable page selection)
   - **Text-based PDFs**: Text-based LLM fallback with OCR snippet
   - Fields grouped (header, addresses, Canadian taxes, line items) for efficient processing
   - Minimal, sanitized payload + OCR snippet + images (for multimodal)
   - TTL cache with LRU eviction for LLM responses and rendered images
   - Async execution with exponential backoff; intelligent rate limit handling (429 errors); partial success tracking
5) **Validation**: Suggestions parsed/sanitized/validated; only applied if confidence improves; dynamic confidence scoring based on correction context; aggregation validator ensures totals consistency.  
6) **HITL Review**: Streamlit UI fetches live data (no cache), shows LLM suggestions side-by-side; user edits and explicitly saves to DB. Offline queue retries on failure.  
7) **Processing States**: PENDING → PROCESSING → EXTRACTED → VALIDATED → STAGED (5-state workflow, simplified from enterprise version).  
8) **ERP Staging**: Stage invoices for ERP export (JSON, CSV, XML, Dynamics GP formats).

## Storage and Deployment (from vanilla architecture)
- Raw files: local storage by default (e.g., `./storage/raw/`); Azure Blob optional via config.
- Database: SQLite by default for dev; Azure SQL for production via `DATABASE_URL`.
- Deployment: local `uvicorn api.main:app --reload`; Docker Compose optional; Streamlit runs separately on 8501.
- Configuration via `.env` (Azure DI, Azure OpenAI, storage, DB).

## Key Components (code anchors)

### API Layer (33 routes across 9 modules)
- **API entry**: `api/main.py` (simplified, no authentication middleware)
- **Ingestion** (6 routes): `api/routes/ingestion.py`, `src/ingestion/ingestion_service.py`, `src/ingestion/azure_blob_utils.py`, `src/ingestion/file_handler.py`
- **Extraction** (3 routes): `api/routes/extraction.py`, `src/extraction/extraction_service.py` (async LLM orchestration, multimodal fallback), `src/extraction/field_extractor.py` (maps DI to 80 canonical fields), `src/extraction/subtype_extractors.py` (invoice subtype-specific extraction), `src/extraction/document_intelligence_client.py`
- **HITL** (9 routes): `api/routes/hitl.py`, `streamlit_app.py` (Streamlit UI for invoice review)
- **Matching** (2 routes): `api/routes/matching.py`, `src/matching/matching_service.py` (simplified)
- **Staging** (4 routes): `api/routes/staging.py`, `src/erp/staging_service.py` (JSON, CSV, XML, Dynamics GP formats)
- **Azure Import** (4 routes): `api/routes/azure_import.py` (container/blob listing, extraction triggers)
- **Batch** (3 routes): `api/routes/batch.py` (batch processing, status tracking)
- **Progress** (1 route): `api/routes/progress.py`, `src/services/progress_tracker.py` (real-time progress tracking)
- **Overlay** (1 route): `api/routes/overlay.py` (PDF overlay generation)

### Core Services (9 major modules)
- **Extraction**: `src/extraction/` - Document Intelligence client, field extractor, subtype extractors (Standard, Shift Service, Per Diem Travel), LLM fallback (text + multimodal)
- **Ingestion**: `src/ingestion/` - Ingestion service, file handler, PDF processor, Azure blob utilities
- **Matching**: `src/matching/` - PO matching service
- **ERP**: `src/erp/` - Staging service, PDF overlay renderer
- **Services**: `src/services/` - Database service, progress tracker, validation service, batch processing service
- **Validation**: `src/validation/aggregation_validator.py` - Validates line item totals, subtotals, taxes consistency
- **Metrics**: `src/metrics/` - Field metrics, document metrics, line item metrics, confidence calibration, ground truth loader
- **Models**: `src/models/` - Invoice models with 3 subtypes, line item DB models (separate table), database utilities
- **Utils**: `src/utils/retry.py` - Retry logic with exponential backoff

### Schemas
- **Canonical schema**: `schemas/invoice.canonical.v1.schema.json` (80 canonical fields)
- **HITL view schema**: `schemas/invoice.hitl_view.v1.schema.json` (13 HITL view fields)
- **Contract schema**: `schemas/invoice.contract.v1.schema.json` (9 contract fields)

### Testing (66 test files)
- **Unit tests** (33 files): `tests/dev/unit/` - Core logic, services, models
- **Integration tests** (29 files): `tests/dev/integration/`, `tests/prod/integration/` - API endpoints, database operations, real service tests
- **E2E tests** (4 files): `tests/demo/e2e/`, `tests/prod/e2e/` - End-to-end workflows, performance testing

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
- **Database**: SQLite (dev) or Azure SQL (prod) via SQLAlchemy/AsyncSession.  
- **Database migrations**: 6 migrations (Alembic) tracking schema evolution
- **Line Items Storage**: Separate `LineItem` table (not JSON column) with foreign key relationship to `Invoice` table. Provides better query performance and referential integrity.
- **Schema contracts**: 
  - **Canonical schema**: `schemas/invoice.canonical.v1.schema.json` (80 canonical fields, 7 required, 3 with validators)
  - **HITL view schema**: `schemas/invoice.hitl_view.v1.schema.json` (13 HITL view fields)
  - **Contract schema**: `schemas/invoice.contract.v1.schema.json` (9 contract fields)
- **Field coverage**: 
  - **80 canonical fields** extractable from Azure Document Intelligence and supported in LLM fallback (text-based and multimodal)
  - Field-level confidence scores tracked for all extracted fields
  - All 80 fields supported in both DI extraction and LLM fallback
- **Invoice Subtypes**: 3 supported subtypes with subtype-specific field extraction:
  - **Standard Invoice**: Standard goods/services structure
  - **Shift Service Invoice**: Shift-based services with timesheet support
  - **Per Diem Travel Invoice**: Travel/training invoices with per-diem rates
- **Field mapping**: `FieldExtractor` maps DI output to canonical `Invoice`; totals/POs prefer DI native values; line-item tax handling merges PST/QST, derives combined tax, applies acceptance %.  
- **Confidence tracking**: Field-level confidence scores tracked for all 80 extracted fields.
- **Validation**: Aggregation validator ensures consistency between invoice-level totals (subtotal, tax, total) and sum of line item amounts.
- **Processing states**: PENDING → PROCESSING → EXTRACTED → VALIDATED → STAGED (5-state workflow)

## HITL UI (Streamlit)
- Fresh fetch (no cache) for invoice list/details.  
- Side-by-side LLM suggestions; explicit “Save to DB” and “Submit Validation”.  
- Live total metric updates with edits.  
- Offline queue for saves with retry; DB health check button; Azure Blob browser to trigger ingestion.

## Observability and Ops
- **Logging**: Standard logging around ingestion, LLM inputs/outputs/diffs, DB health (no structured JSON logging or correlation IDs).  
- **Progress Tracking**: Real-time progress tracking via `ProgressTracker` service with step-by-step status updates for extraction operations.
- **Metrics Module**: Comprehensive evaluation tools for extraction performance:
  - Field-level metrics (per-field accuracy, precision, recall)
  - Document-level metrics (overall document accuracy)
  - Line item metrics (line item extraction accuracy)
  - Confidence calibration metrics (confidence score calibration analysis)
  - Ground truth loader for evaluation datasets
- **Health endpoints**: `/api/health` (basic), `/api/ingestion/health/db` (database connectivity).  
- **Operations**: Blob listing/extraction triggers, batch processing, progress tracking endpoints.

## Security Notes
- **Secrets management**: Azure Key Vault integration with environment variable fallback (same pattern as Vanilla). Secrets for Document Intelligence, Azure OpenAI, Azure Storage loaded from Key Vault first, then `.env`.  
- **No authentication**: API routes do not require authentication (demo-focused). No Azure AD integration, no JWT validation, no RBAC.  
- **No secrets in code**: All secrets via Key Vault or `.env`; archives containing `.env` should be handled carefully.  
- **DEMO_MODE**: Flag to bypass Azure dependencies with mock implementations (for development/testing without credentials).

## Testing and Quality (Test Pyramid)

**Comprehensive test suite (66 test files) organized by environment (DEMO/DEV/PROD) and test pyramid level (unit/integration/e2e):**

### Test Organization

- **Unit tests** (33 files, `tests/dev/unit/`): 
  - Field extractor mapping/line-item logic, JSON sanitizer/prompt builder in `extraction_service`
  - Safe decimal parsing in HITL routes
  - Aggregation validator logic
  - Progress tracker, retry logic, validation service
  - Database persistence, concurrency, atomic updates
  - PDF processor, document intelligence client
  - Core extraction and validation logic

- **Integration tests** (29 files):
  - **DEV** (`tests/dev/integration/`): FastAPI route tests (ingestion/hitl) with DI/LLM mocked, DB health endpoint tests, HITL validation workflows
  - **PROD** (`tests/prod/integration/`): Real service integration tests with isolated test databases
    - **Real DI extraction tests** (`test_real_di_extraction.py`) - validates all 80 canonical fields
    - **Real LLM extraction tests** (`test_real_llm_extraction.py`) - validates 80 fields with full pipeline
    - **Real multimodal LLM extraction tests** (`test_real_multimodal_llm_extraction.py`) - validates 80 fields with scanned PDF detection and image rendering
    - **Standalone extraction tests** (`tests/demo/integration/`) - no database, direct service testing
    - **Error handling tests** - LLM API failures, rate limiting, network issues, multimodal image rendering failures
    - **Performance tests** - multimodal LLM image rendering performance, response times

- **E2E tests** (4 files):
  - Streamlit + API happy path (`tests/demo/e2e/`, `tests/prod/e2e/`)
  - Upload/ingest/extract/review/save flows
  - Performance and scalability tests

### Test Infrastructure

- **Test pyramid compliant**: ~2:1:0.1 ratio (33 unit : 29 integration : 4 e2e)
- **Coverage target**: 75% minimum code coverage
- **Static analysis**: Python type hints, Pydantic validation
- **Test organization**: Comprehensive fixtures, isolated test databases, async support, real PDF test data
- **Resilience checks**: LLM fallback grouping/backoff, 429 handling, offline queue for saves (UI), partial success handling, retry logic with exponential backoff, multimodal image rendering error handling

**Test organization**: Tests organized by environment (DEMO=standalone, DEV=mocked, PROD=real services) and test pyramid level for clear separation of concerns.

## Key Differences from Vanilla (Production-Ready Version)

**DEMO focuses on extraction capabilities and comprehensive testing, NOT production-ready features:**

- ❌ **No authentication/authorization** (no Azure AD, no JWT, no RBAC)
- ❌ **No approval workflows** (no Sec34/Sec33 approvals, simplified 5-state workflow: PENDING → STAGED)
- ❌ **No SharePoint integration** (no sync/webhooks via Microsoft Graph)
- ❌ **No Dynamics GP direct export** (basic ERP staging with JSON/CSV/XML/Dynamics GP formats)
- ❌ **No observability features** (no structured JSON logging, correlation IDs, trace context, metrics emission)
- ❌ **No React frontend** (Streamlit HITL UI only)
- ❌ **No audit logging** (no centralized audit trails)
- ❌ **No event sourcing or saga patterns** (simplified architecture)
- ❌ **No ML observability platform** (no A/B testing, model registry)
- ✅ **80 canonical fields** (all fields supported in both DI extraction and LLM fallback)
- ✅ **3 invoice subtypes** (Standard, Shift Service, Per Diem Travel) with subtype-specific extraction
- ✅ **Line items as separate table** (not JSON column - better performance and referential integrity)
- ✅ **Comprehensive test suite** (66 test files: 33 unit, 29 integration, 4 e2e)
- ✅ **Metrics module** (field-level, document-level, line item, confidence calibration, ground truth support)
- ✅ **Aggregation validator** (validates totals consistency between invoice-level and line item sums)
- ✅ **Progress tracking** (real-time extraction progress updates for preprocessing, ingestion, extraction, LLM evaluation)
- ✅ **Multimodal LLM support** (automatic scanned PDF detection, image rendering with caching)
- ✅ **TTL caching** (LRU cache with TTL for LLM responses and rendered PDF images)
- ✅ **Retry logic** (exponential backoff with rate limit handling for 429 errors)

## Current Implementation Status

### Fully Implemented ✅
- ✅ **33 API routes** across 9 modules (ingestion, extraction, HITL, matching, staging, azure_import, batch, progress, overlay)
- ✅ **80 canonical fields** (all fields supported in DI extraction and LLM fallback)
- ✅ **3 invoice subtypes** (Standard, Shift Service, Per Diem Travel) with subtype-specific extractors
- ✅ **5-state workflow** (PENDING → PROCESSING → EXTRACTED → VALIDATED → STAGED)
- ✅ **LLM fallback** (text-based and multimodal) with rate limit handling and partial success tracking
- ✅ **Retry logic** with exponential backoff for Azure service calls (429 errors)
- ✅ **TTL caching** with LRU eviction for LLM responses and rendered PDF images
- ✅ **Progress tracking** for real-time extraction status updates
- ✅ **Aggregation validator** for totals consistency validation
- ✅ **Metrics module** (field-level, document-level, line item, confidence calibration)
- ✅ **6 database migrations** tracking schema evolution
- ✅ **66 test files** (33 unit, 29 integration, 4 e2e) with test pyramid compliance
- ✅ **9 major source modules** with clear separation of concerns
- ✅ **32 direct Python dependencies**

### Future Considerations
- Circuit-breaker for repeated 429s (not yet implemented - not needed for demo)
- Formal SLIs/SLOs for latency and fallback success (not needed for demo)
- AuthN/Z hardening for APIs and Streamlit (not needed for demo)
- SharePoint integration via Microsoft Graph API (can be added if needed)

