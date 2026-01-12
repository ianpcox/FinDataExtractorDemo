# Architecture Overview - FinDataExtractor DEMO

## System Architecture

FinDataExtractor DEMO is a demonstration-focused invoice processing system emphasizing extraction capabilities, comprehensive testing, and evaluation tools. It is designed for showcasing extraction features rather than production deployment.

### System Metrics (as of latest update)
- **33 API routes** across **9 modules** (ingestion, extraction, HITL, matching, staging, azure_import, batch, progress, overlay)
- **9 major source modules** under `src/`
- **66 test files** (33 unit, 29 integration, 4 e2e)
- **80 canonical fields** in invoice schema (7 required, 3 with validators)
- **3 invoice subtypes**: Standard Invoice, Shift Service Invoice, Per Diem Travel Invoice
- **6 database migrations** (Alembic) tracking schema evolution
- **32 direct Python dependencies**

```
┌─────────────────┐
│   PDF Invoices  │
│   (Input)       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│      Ingestion Service              │
│  - File validation                  │
│  - Storage (local or Azure)         │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│    Data Extraction Engine           │
│  - Azure Document Intelligence      │
│  - Extract 53 canonical fields      │
│  - Field-level confidence scores    │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│    LLM Fallback (Optional)          │
│  - Text-based LLM (text PDFs)       │
│  - Multimodal LLM (scanned PDFs)    │
│  - Image rendering & caching        │
│  - Dynamic confidence scoring       │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│    Document Matching                │
│  - PO matching (simplified)         │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│    API Layer                        │
│  - REST API (FastAPI)               │
│  - HITL endpoints                   │
└─────────────────────────────────────┘
```

## Components

### 1. Ingestion Service

**Purpose**: Accept and validate PDF invoices

**Responsibilities**:
- Accept file uploads (single or batch)
- Validate PDF format
- Store files (local or Azure Blob Storage)
- Create processing records

**Key Files**:
- `src/ingestion/file_handler.py` - File storage handler
- `src/ingestion/pdf_processor.py` - PDF validation
- `src/ingestion/ingestion_service.py` - Ingestion orchestration

### 2. Data Extraction Engine

**Purpose**: Extract structured data from PDF invoices with comprehensive field coverage (80 canonical fields)

**Responsibilities**:
- Analyze invoices with Azure Document Intelligence
- Extract **all 80 canonical invoice fields** with field-level confidence scores
- **Invoice subtype detection** (Standard, Shift Service, Per Diem Travel) for subtype-specific field extraction
- Map DI output to canonical Invoice model via `FieldExtractor` (all 80 fields supported in both DI extraction and LLM fallback)
- LLM fallback for low-confidence fields:
  - **Text-based LLM**: For text-based PDFs, uses OCR snippet (beginning, middle, end sections) and field values
  - **Multimodal LLM**: For scanned/image-based PDFs, uses rendered PDF page images (PNG/JPEG, base64) + text
  - Automatic scanned PDF detection
  - Image rendering with PyMuPDF, caching (TTL + LRU), multiple formats (PNG/JPEG with quality control), configurable page selection (first/last/middle/all)
  - Supports **all 80 canonical fields** in LLM fallback (text-based and multimodal)
- Dynamic confidence scoring based on correction context (filled blank vs corrected wrong value vs confirmed existing)
- Response validation before applying LLM suggestions (date formats, amount ranges, address structure)
- Async grouped execution with partial success tracking
- Rate limit handling (429 errors) with intelligent backoff

**Key Files**:
- `src/extraction/document_intelligence_client.py` - Azure Document Intelligence client (extracts all 80 fields)
- `src/extraction/extraction_service.py` - Extraction orchestration with async LLM fallback (text + multimodal)
- `src/extraction/field_extractor.py` - DI to canonical field mapping (all 80 fields)
- `src/extraction/subtype_extractors.py` - Invoice subtype-specific extraction logic (Standard, Shift Service, Per Diem Travel)

### 3. Document Matching

**Purpose**: Match invoices to purchase orders with simplified implementation

**Responsibilities**:
- Match invoices to POs by PO number
- Confidence scoring
- Basic matching logic (simplified for demo purposes)

**Key Files**:
- `src/matching/matching_service.py` - Matching logic (simplified implementation)

### 4. API Layer

**Purpose**: Provide REST API for system interaction (33 routes across 9 modules, no authentication required - demo-focused)

**API Structure**:
- **Ingestion** (6 routes): `POST /api/ingestion/upload`, `POST /api/ingestion/batch-upload`, `GET /api/ingestion/blobs`, `POST /api/ingestion/extract-blob`, `GET /api/ingestion/status/{invoice_id}`, `GET /api/ingestion/health/db`
- **Extraction** (3 routes): `POST /api/extraction/extract/{invoice_id}`, `GET /api/extraction/{invoice_id}`, `GET /api/progress/{invoice_id}`
- **HITL** (9 routes): `GET /api/hitl/invoice/list`, `GET /api/hitl/invoice/{invoice_id}`, `POST /api/hitl/invoice/validate`, plus field update endpoints
- **Matching** (2 routes): `POST /api/matching/match`, `GET /api/matching/{invoice_id}/matches`
- **Staging** (4 routes): `POST /api/staging/stage`, `POST /api/staging/batch-stage`, `GET /api/staging/{invoice_id}`, `GET /api/staging/list`
- **Azure Import** (4 routes): `GET /api/azure-import/list-containers`, `GET /api/azure-import/list-blobs`, `POST /api/azure-import/extract-blob`
- **Batch** (3 routes): `POST /api/batch/process`, `GET /api/batch/status/{batch_id}`, `GET /api/batch/list`
- **Progress** (1 route): `GET /api/progress/{invoice_id}` (real-time progress tracking)
- **Overlay** (1 route): `GET /api/overlay/{invoice_id}/pdf` (PDF overlay generation)
- **Health**: `GET /health` (basic health check)

**Key Files**:
- `api/main.py` - FastAPI application (simplified, no authentication middleware)
- `api/routes/` - Route handlers organized by feature domain (9 modules)

## Data Models

### Invoice Model

Comprehensive invoice model with support for 3 subtypes and 80 canonical fields:

**Core Fields**:
- Basic information (invoice_number, invoice_date, due_date, invoice_type)
- Vendor information (vendor_name, vendor_id, vendor_address, tax registration numbers)
- Customer/Bill-To information
- Financial fields (subtotal, tax_amount, total_amount, currency)
- **Line items stored in separate `LineItem` table** (not JSON column) for better query performance and referential integrity
- Review status (review_version, review_status, review_timestamp)
- **80 canonical fields** extractable from Document Intelligence and supported in LLM fallback (all 80 fields in both DI and LLM)
- Field-level confidence scores for all extracted fields

**Invoice Subtypes** (3 supported):
- **Standard Invoice**: Standard goods/services structure
- **Shift Service Invoice**: Shift-based services with timesheet support
  - Extensions: `service_location`, `billing_period_start/end`, `shift_rate`, `total_shifts_billed`, `timesheet_data`
- **Per Diem Travel Invoice**: Travel/training invoices with per-diem rates
  - Extensions: `traveller_id`, `traveller_name`, `programme_or_course_code`, `work_location`, `destination_location`, `travel_from_date`, `travel_to_date`, `daily_rate`

**Processing States** (5-state workflow):
- **PENDING** → **PROCESSING** → **EXTRACTED** → **VALIDATED** → **STAGED**

**Schema Variants**:
- **Canonical schema**: `schemas/invoice.canonical.v1.schema.json` (80 canonical fields, 7 required, 3 with validators)
- **HITL view schema**: `schemas/invoice.hitl_view.v1.schema.json` (13 HITL view fields)
- **Contract schema**: `schemas/invoice.contract.v1.schema.json` (9 contract fields)

See `src/models/invoice.py` and `src/models/line_item_db_models.py` for complete details.

## Storage Options

### Local Storage (Default)

Files are stored in the local filesystem:
- Path: `./storage/raw/` (configurable)
- Simple file-based storage
- No external dependencies

### Azure Blob Storage (Optional)

Files can be stored in Azure Blob Storage:
- Requires Azure Storage account
- Configured via environment variables
- Automatic fallback to local storage if Azure is unavailable

## Database

### SQLite (Default)

- Local SQLite database for development
- File: `./findataextractor.db`
- No external database server required

### Azure SQL (Optional)

- Can be configured for production
- Requires Azure SQL Database
- Configured via `DATABASE_URL` environment variable

## Configuration

Configuration is managed via environment variables with Azure Key Vault integration for secrets (see `.env.example`):

### Required Settings

- **Azure Document Intelligence**: `AZURE_FORM_RECOGNIZER_ENDPOINT`, `AZURE_FORM_RECOGNIZER_KEY` (from Key Vault or env var)

### Optional Settings

- **Azure Storage**: `AZURE_STORAGE_CONNECTION_STRING` (from Key Vault or env var), container names
- **Database**: `DATABASE_URL` (defaults to SQLite), separate line items table
- **Azure OpenAI (Text-based LLM)**: 
  - `AOAI_ENDPOINT`, `AOAI_API_KEY`, `AOAI_DEPLOYMENT_NAME` (from Key Vault or env var)
  - `USE_LLM_FALLBACK` (enable/disable, default: false)
  - `LLM_LOW_CONF_THRESHOLD` (default: 0.75)
  - `LLM_CACHE_TTL_SECONDS` (default: 3600)
  - `LLM_CACHE_MAX_SIZE` (default: 1000)
  - `LLM_OCR_SNIPPET_MAX_CHARS` (default: 3000)
- **Azure OpenAI (Multimodal LLM)**: 
  - `USE_MULTIMODAL_LLM_FALLBACK` (enable/disable, default: false)
  - `AOAI_MULTIMODAL_DEPLOYMENT_NAME` (optional, falls back to `AOAI_DEPLOYMENT_NAME`)
  - `MULTIMODAL_MAX_PAGES` (default: 2)
  - `MULTIMODAL_IMAGE_SCALE` (default: 2.0)
  - `MULTIMODAL_IMAGE_FORMAT` (png/jpeg, default: png)
  - `MULTIMODAL_JPEG_QUALITY` (1-100, default: 85)
  - `MULTIMODAL_PAGE_SELECTION` (first/last/middle/all, default: first)
  - `MULTIMODAL_IMAGE_CACHE_ENABLED` (default: true)
  - `MULTIMODAL_IMAGE_CACHE_TTL_SECONDS` (default: 7200)
  - `MULTIMODAL_IMAGE_CACHE_MAX_SIZE` (default: 500)
- **PDF Preprocessing**: `ENABLE_PDF_PREPROCESSING`, `ENABLE_PDF_IMAGE_OPTIMIZATION`, `ENABLE_PDF_ROTATION_CORRECTION`
- **Demo Mode**: `DEMO_MODE` (bypasses Azure dependencies with mock implementations for testing without credentials)
- **Azure Key Vault**: `AZURE_KEY_VAULT_URL` or `AZURE_KEY_VAULT_NAME` (uses Managed Identity in production)

## Features and Focus

**DEMO is focused on extraction capabilities and comprehensive testing, NOT production-ready features:**

### Implemented Features

**Core Functionality:**
- ✅ **33 API routes** across 9 modules (ingestion, extraction, HITL, matching, staging, azure_import, batch, progress, overlay)
- ✅ Core invoice ingestion (direct upload via API/Streamlit, Azure Blob Storage optional, batch)
- ✅ Data extraction (all 80 canonical fields from DI, all 80 fields supported in LLM fallback)
- ✅ **3 invoice subtypes**: Standard, Shift Service, Per Diem Travel with subtype-specific extraction
- ✅ LLM fallback (text-based and multimodal for scanned PDFs)
- ✅ Image rendering and caching for multimodal LLM (PyMuPDF, TTL + LRU cache)
- ✅ Line items as separate database table (better performance than JSON column, referential integrity)
- ✅ Aggregation validator (validates totals consistency between invoice-level and line item sums)
- ✅ Basic validation and document matching
- ✅ ERP staging (JSON, CSV, XML, Dynamics GP payload formats)
- ✅ PDF overlay generation
- ✅ Progress tracking (real-time extraction progress for preprocessing, ingestion, extraction, LLM evaluation)
- ✅ Metrics module (field-level, document-level, line item, confidence calibration, ground truth support)

**Testing & Quality:**
- ✅ Comprehensive test coverage (66 test files: 33 unit, 29 integration, 4 e2e)
- ✅ Test pyramid compliant (~2:1:0.1 ratio)
- ✅ Coverage target: 75% minimum
- ✅ Static analysis: Python type hints, Pydantic validation

**Operational:**
- ✅ REST API (no authentication - demo-focused)
- ✅ Local or Azure Blob Storage (optional)
- ✅ Azure Key Vault integration (for secrets management)
- ✅ Streamlit HITL UI (web-based invoice review interface)
- ✅ Retry logic with exponential backoff and rate limit handling (429 errors)
- ✅ TTL caching for LLM responses and rendered PDF images
- ✅ Partial success tracking for LLM fallback operations
- ✅ Async processing throughout for non-blocking operations

**Database:**
- ✅ **6 database migrations** (Alembic) tracking schema evolution
- ✅ SQLite (dev) or Azure SQL (prod) via SQLAlchemy async
- ✅ Separate LineItem table with foreign key relationships

### Not Included (vs Production-Ready Vanilla)

- ❌ Authentication/Authorization (no Azure AD, no JWT, no RBAC)
- ❌ Approval workflows (no Sec34/Sec33 approvals, simplified 5-state workflow)
- ❌ SharePoint integration via Microsoft Graph (no sync/webhooks)
- ❌ Dynamics GP direct export (basic staging with payload generation only)
- ❌ Observability features (no structured JSON logging, correlation IDs, trace context, metrics emission)
- ❌ React frontend (Streamlit HITL UI only)
- ❌ Audit logging (no centralized audit trails)
- ❌ API versioning (no version management system)
- ❌ ML observability platform (no A/B testing, model registry, feature store)
- ❌ Event sourcing and saga patterns (no event store or distributed transaction orchestration)
- ❌ Circuit breakers (uses retry/backoff instead)
- ❌ Workflow engine (simplified state transitions, no complex workflow orchestration)
- ❌ Dead letter queues (no DLQ monitoring)
- ❌ Health monitoring (basic health check only, no comprehensive dependency checks)

## Deployment

### Local Development

```bash
uvicorn api.main:app --reload
```

### Docker

```bash
docker-compose up
```

### Production

See deployment documentation for production setup with Azure services.

## Testing

**The system includes comprehensive test coverage (66 test files) organized by environment (DEMO/DEV/PROD) and test pyramid level:**

### Test Organization

Tests are organized in `tests/` directory:
- **DEMO** (`tests/demo/`): Quick, standalone tests for demonstrations (no database, script-style)
- **DEV** (`tests/dev/`): Development tests with mocks (fast, CI/CD suitable, isolated test databases)
- **PROD** (`tests/prod/`): Production tests with real services (requires Azure credentials, may incur costs)

### Test Pyramid

- **Unit Tests** (33 files, `tests/dev/unit/`): 
  - Field extraction, mapping, validation logic
  - Aggregation validator
  - JSON sanitizer, prompt builder
  - Progress tracker, retry logic, validation service
  - Database persistence, concurrency, atomic updates
  - PDF processor, document intelligence client
  - Subtype extractors

- **Integration Tests** (29 files):
  - **DEV** (`tests/dev/integration/`): API endpoints with mocked services, database operations, HITL workflows
  - **PROD** (`tests/prod/integration/`): Real service integration tests with isolated test databases
    - **Real DI extraction** (`test_real_di_extraction.py`) - validates all 80 canonical fields
    - **Real LLM extraction** (`test_real_llm_extraction.py`) - validates 80 fields with text-based LLM
    - **Real Multimodal LLM extraction** (`test_real_multimodal_llm_extraction.py`) - validates 80 fields with vision-capable LLM
    - **Standalone extraction tests** (`tests/demo/integration/`) - no database, direct service testing
    - **Error handling tests** - LLM API failures, rate limiting, network issues, multimodal image rendering failures
    - **Performance tests** - multimodal LLM image rendering performance, response times

- **E2E Tests** (4 files):
  - Streamlit + API happy path (`tests/demo/e2e/`, `tests/prod/e2e/`)
  - Performance and scalability tests

### Test Infrastructure

- **Test pyramid compliant**: ~2:1:0.1 ratio (33 unit : 29 integration : 4 e2e)
- **Coverage target**: 75% minimum code coverage
- **Static analysis**: Python type hints, Pydantic validation
- **Test organization**: Comprehensive fixtures, isolated test databases, async support, real PDF test data

### Coverage Verification

- DI canonical field coverage: **80 fields** (all canonical fields supported)
- LLM canonical field coverage: **80 fields** (text-based LLM supports all 80 fields)
- Multimodal LLM canonical field coverage: **80 fields** (multimodal LLM supports all 80 fields)

All real service tests use isolated test databases and proper cleanup to avoid conflicts.

## Documentation

### Extraction Documentation
- **LLM Behavior**: `LLM_BEHAVIOR_DOCUMENTATION.md` - Documents text-based LLM fallback behavior, confidence scoring, formatting rules, 57 field coverage
- **Multimodal LLM Behavior**: `MULTIMODAL_LLM_BEHAVIOR_DOCUMENTATION.md` - Documents multimodal LLM fallback, image rendering, scanned PDF detection, 57 field coverage
- **DI Mapping Verification**: `DI_MAPPING_VERIFICATION_REPORT.md` - Verifies all 53 DI field mappings are correct

### Testing Documentation
- **Test Organization**: `tests/README.md` - Comprehensive guide to test structure, organization by environment (DEMO/DEV/PROD), and test pyramid
- **Test Reports**: `tests/reports/README.md` - Guide to test reports and analysis tools

### Architecture Documentation
- **ARB Architecture Overview**: `docs/ARB-architecture-overview.md` - High-level architecture brief
- **Architecture**: `docs/ARCHITECTURE.md` - This document

## Additional Components

### Metrics Module

Comprehensive evaluation tools for extraction performance:
- **Field Metrics** (`src/metrics/field_metrics.py`): Per-field accuracy, precision, recall
- **Document Metrics** (`src/metrics/document_metrics.py`): Overall document accuracy
- **Line Item Metrics** (`src/metrics/line_item_metrics.py`): Line item extraction accuracy
- **Confidence Calibration** (`src/metrics/confidence_calibration.py`): Confidence score calibration analysis
- **Ground Truth Loader** (`src/metrics/ground_truth_loader.py`): Load evaluation datasets

### Progress Tracking

Real-time progress tracking for extraction operations:
- `src/services/progress_tracker.py`: Step-by-step progress tracking
- `api/routes/progress.py`: Progress API endpoint
- Provides current step, progress percentage, status, and detailed step information

### Validation

- **Aggregation Validator** (`src/validation/aggregation_validator.py`): Validates consistency between invoice-level totals (subtotal, tax, total) and sum of line item amounts

