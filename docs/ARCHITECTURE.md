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
│  - Field extraction                 │
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
│  - No versioning                    │
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
- Extract invoice fields (number, date, amount, vendor, line items)
- Map to Invoice model

**Key Files**:
- `src/extraction/document_intelligence_client.py` - Azure client
- `src/extraction/extraction_service.py` - Extraction orchestration

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
- **Storage**: Optional (defaults to local)
- **Database**: Optional (defaults to SQLite)

## Simplifications vs Full Version

This vanilla version removes:
- ❌ API versioning
- ❌ ML observability
- ❌ Event sourcing
- ❌ Saga patterns
- ❌ Circuit breakers
- ❌ Dead letter queues
- ❌ Complex workflow orchestration
- ❌ Azure Key Vault integration
- ❌ Advanced retry logic

This vanilla version keeps:
- ✅ Core invoice ingestion
- ✅ Data extraction
- ✅ Basic validation
- ✅ Simple document matching
- ✅ REST API
- ✅ Local or Azure storage

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

