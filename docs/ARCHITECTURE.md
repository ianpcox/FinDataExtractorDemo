# Architecture Overview - FinDataExtractor Vanilla

## System Architecture

FinDataExtractor Vanilla is a simplified invoice processing system with the following components:

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

**Purpose**: Extract structured data from PDF invoices

**Responsibilities**:
- Analyze invoices with Azure Document Intelligence
- Extract all 53 canonical invoice fields with field-level confidence scores
- Map DI output to canonical Invoice model via `FieldExtractor`
- LLM fallback for low-confidence fields:
  - **Text-based LLM**: For text-based PDFs, uses OCR snippet and field values
  - **Multimodal LLM**: For scanned/image-based PDFs, uses rendered PDF page images (PNG/JPEG) + text
  - Automatic scanned PDF detection
  - Image rendering with caching, multiple formats, configurable page selection
- Dynamic confidence scoring based on correction context
- Response validation before applying LLM suggestions

**Key Files**:
- `src/extraction/document_intelligence_client.py` - Azure Document Intelligence client (extracts all 53 fields)
- `src/extraction/extraction_service.py` - Extraction orchestration with LLM fallback
- `src/extraction/field_extractor.py` - DI to canonical field mapping

### 3. Document Matching

**Purpose**: Match invoices to purchase orders

**Responsibilities**:
- Match invoices to POs (simplified implementation)
- Confidence scoring

**Key Files**:
- `src/matching/` - Matching logic (to be implemented)

### 4. API Layer

**Purpose**: Provide REST API for system interaction

**Endpoints**:
- `POST /api/ingestion/upload` - Upload invoice
- `POST /api/ingestion/batch-upload` - Upload multiple invoices
- `POST /api/extraction/extract/{invoice_id}` - Extract data
- `POST /api/matching/match` - Match invoice to PO

**Key Files**:
- `api/main.py` - FastAPI application
- `api/routes/` - Route handlers

## Data Models

### Invoice Model

Simplified invoice model with core fields:
- Basic information (number, date, vendor)
- Financial fields (subtotal, tax, total)
- Line items
- Review status

See `src/models/invoice.py` for details.

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

All configuration is done via environment variables (see `.env.example`):

- **Azure Document Intelligence**: Required for extraction
  - `AZURE_FORM_RECOGNIZER_ENDPOINT`
  - `AZURE_FORM_RECOGNIZER_KEY`
- **Azure OpenAI (Text-based LLM)**: Optional for LLM fallback
  - `AOAI_ENDPOINT`
  - `AOAI_API_KEY`
  - `AOAI_DEPLOYMENT_NAME`
  - `USE_LLM_FALLBACK` (enable/disable)
  - `LLM_LOW_CONF_THRESHOLD` (default: 0.75)
  - `LLM_CACHE_TTL_SECONDS` (default: 3600)
  - `LLM_CACHE_MAX_SIZE` (default: 1000)
- **Azure OpenAI (Multimodal LLM)**: Optional for scanned PDF fallback
  - `USE_MULTIMODAL_LLM_FALLBACK` (enable/disable)
  - `AOAI_MULTIMODAL_DEPLOYMENT_NAME` (optional, falls back to `AOAI_DEPLOYMENT_NAME`)
  - `MULTIMODAL_MAX_PAGES` (default: 2)
  - `MULTIMODAL_IMAGE_SCALE` (default: 2.0)
  - `MULTIMODAL_IMAGE_FORMAT` (png/jpeg, default: png)
  - `MULTIMODAL_JPEG_QUALITY` (1-100, default: 85)
  - `MULTIMODAL_PAGE_SELECTION` (first/last/middle/all, default: first)
  - `MULTIMODAL_IMAGE_CACHE_ENABLED` (default: true)
  - `MULTIMODAL_IMAGE_CACHE_TTL_SECONDS` (default: 7200)
  - `MULTIMODAL_IMAGE_CACHE_MAX_SIZE` (default: 500)
- **Storage**: Optional (defaults to local)
- **Database**: Optional (defaults to SQLite)

## Simplifications vs Full Version

This vanilla version removes:
-  API versioning
-  ML observability
-  Event sourcing
-  Saga patterns
-  Circuit breakers
-  Dead letter queues
-  Complex workflow orchestration
-  Azure Key Vault integration
-  Advanced retry logic

This vanilla version keeps:
-  Core invoice ingestion
-  Data extraction (all 53 canonical fields from DI)
-  LLM fallback (text-based and multimodal for scanned PDFs)
-  Image rendering and caching for multimodal LLM
-  Basic validation
-  Simple document matching
-  REST API
-  Local or Azure storage
-  Comprehensive test coverage (unit, integration, real service tests)

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

The system includes comprehensive test coverage:

- **Unit Tests**: Field extraction, mapping, validation logic
- **Integration Tests**: API endpoints, database operations
- **Real Service Tests**: 
  - Real Azure Document Intelligence extraction (`tests/integration/test_real_di_extraction.py`)
  - Real Azure OpenAI LLM extraction (`tests/integration/test_real_llm_extraction.py`)
  - Real Azure OpenAI Multimodal LLM extraction (`tests/integration/test_real_multimodal_llm_extraction.py`)
  - Error handling tests for LLM and multimodal LLM
- **Coverage Reports**: 
  - DI canonical field coverage (53 fields)
  - LLM canonical field coverage (57 fields)
  - Multimodal LLM canonical field coverage (57 fields)

All real service tests use isolated test databases and proper cleanup to avoid conflicts.

## Documentation

- **LLM Behavior**: `LLM_BEHAVIOR_DOCUMENTATION.md` - Documents text-based LLM fallback behavior, confidence scoring, formatting rules
- **Multimodal LLM Behavior**: `MULTIMODAL_LLM_BEHAVIOR_DOCUMENTATION.md` - Documents multimodal LLM fallback, image rendering, scanned PDF detection
- **DI Mapping Verification**: `DI_MAPPING_VERIFICATION_REPORT.md` - Verifies all DI field mappings are correct

