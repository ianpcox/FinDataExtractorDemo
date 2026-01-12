# FinDataExtractor Vanilla - Simplified Invoice Processing

## Overview

**FinDataExtractor Vanilla** is a simplified, easy-to-use version of the FinDataExtractor system designed for CATSA users who need core invoice processing capabilities without the complexity of advanced features.

This version focuses on:
-  **Simple PDF invoice ingestion**
-  **Core data extraction** (invoice number, date, amount, vendor, line items)
-  **Basic validation** (format checks, required fields)
-  **Document matching** (invoice to PO matching)
-  **Straightforward API** (no versioning complexity)
-  **Easy setup** (minimal configuration)

## Relationship to Full Version

This is a **simplified fork** of the main [FinDataExtractor](../FinDataExtractor) project. The full version includes advanced features like:
- ML observability and A/B testing
- Event sourcing and saga patterns
- Complex workflow orchestration
- Advanced Azure Key Vault integration
- API versioning
- Dead letter queues
- Circuit breakers and retry logic

**When to use Vanilla:**
- You need basic invoice processing
- You want simple setup and configuration
- You don't need advanced ML features
- You prefer straightforward documentation

**When to use Full Version:**
- You need enterprise-grade features
- You require ML observability
- You need complex workflow orchestration
- You want advanced error handling patterns

## System at a Glance

### Capability Summary

| **Capability** | **Details** |
|----------------|-------------|
| **Ingestion Sources** | Direct upload (API/Streamlit), Azure Blob Storage (optional) |
| **Processing States** | PENDING → PROCESSING → EXTRACTED → VALIDATED → STAGED |
| **Invoice Subtypes** | Standard Invoice, Shift Service Invoice, Per Diem Travel Invoice |
| **ERP Payload Formats** | JSON, CSV, XML, Dynamics GP (XML) |
| **LLM Fallback** | Text-based LLM for text PDFs, Multimodal LLM for scanned PDFs |
| **Extraction Coverage** | 80 canonical fields with field-level confidence scores |

### API Surface

- **33 total routes** across **9 modules**:
  - **Ingestion** (6): Upload, batch upload, blob listing, Azure import
  - **Extraction** (3): Extract invoice, get extraction status, progress tracking
  - **HITL** (9): Invoice list, detail, validation, field updates
  - **Matching** (2): Match invoice to PO, get matches
  - **Staging** (4): Stage invoice, batch stage, get staged invoices
  - **Azure Import** (4): Container/blob listing, extraction triggers
  - **Batch** (3): Batch processing, status tracking
  - **Progress** (1): Real-time progress tracking
  - **Overlay** (1): PDF overlay generation

### Schema & Contracts

- **80 canonical fields** (invoice.canonical.v1.schema.json)
- **13 HITL view fields** (invoice.hitl_view.v1.schema.json)
- **3 schema variants**: Canonical, HITL View, Contract
- **Field-level confidence scores** for all extracted fields
- **Multimodal LLM support** for scanned/image-based PDFs

### Quality Posture

- **66 test files**:
  - **33 unit tests** (fast, isolated, mocked)
  - **29 integration tests** (database integration, API flows, real PDF processing)
  - **4 E2E tests** (end-to-end workflows, performance testing)
  - Test pyramid compliant (~2:1:0.1 ratio)
- **Coverage Target**: 75% minimum (run `pytest --cov=src` to see current coverage)
- **Static Analysis**: Python type hints, Pydantic validation
- **Test Organization**: Comprehensive fixtures, isolated test databases, async support, real PDF test data

### Operational Hardening

- ✅ **Progress Tracking**: Real-time progress tracking for preprocessing, ingestion, extraction, and LLM evaluation
- ✅ **Retry Logic**: Exponential backoff for Azure service calls
- ✅ **Rate Limit Handling**: Intelligent handling of 429 errors with backoff
- ✅ **TTL Caching**: LRU cache with TTL for LLM responses and rendered PDF images
- ✅ **Partial Success Tracking**: LLM fallback operations track partial success
- ✅ **Error Handling**: Comprehensive error handling with graceful degradation
- ✅ **Async Processing**: Async/await throughout for non-blocking operations
- ✅ **Multimodal Support**: Automatic detection and handling of scanned vs text-based PDFs
- ✅ **Batch Processing**: Batch operations for ingestion, extraction, and staging

### Code Organization

- **9 major modules** under `src/`: `erp`, `extraction`, `ingestion`, `matching`, `metrics`, `models`, `services`, `utils`, `validation`
- **9 API route modules** organized by feature domain
- **6 database migrations** (Alembic) tracking schema evolution
- **Streamlit HITL UI**: Web-based interface for invoice review and validation

### Dependencies

- **32 direct Python dependencies** (see `requirements.txt`)
- **Key technologies**: 
  - Backend: FastAPI, SQLAlchemy (async), Azure SDKs, Pydantic v2
  - UI: Streamlit
  - PDF Processing: PyMuPDF, pdfplumber, PyPDF2
  - LLM: Azure OpenAI (text and multimodal GPT-4 Vision)
- **Optional dependencies**: Azure services (DI, OpenAI, Blob Storage), Azure SQL for production

### Evaluation & Metrics Capabilities

The system includes evaluation tools for extraction performance assessment:

- **Field-level metrics**: Precision, recall, F1 score, accuracy per field
- **Document-level metrics**: Extraction rate, hard pass evaluation
- **Line item metrics**: Line item count accuracy, aggregation validation
- **Confidence calibration**: Confidence score calibration analysis
- **Ground truth support**: Ground truth data loading and comparison utilities

*To compute evaluation metrics, use the metrics module tools (see `src/metrics/`)*

### Repository Health

*Stats generated automatically - run `python scripts/generate_project_stats.py --markdown` for current metrics*

**Current Metrics** (as of last update):
- **33 API routes** across 9 modules
- **80 canonical fields** in invoice schema (7 required)
- **66 test files** (33 unit, 29 integration, 4 e2e)
- **6 database migrations** tracking schema evolution
- **9 major source modules** with clear separation of concerns
- **32 direct Python dependencies**

**To update metrics:**
```bash
# Generate current project statistics
python scripts/generate_project_stats.py --markdown

# Run test coverage report
pytest --cov=src --cov-report=term --cov-report=html

# Check for dependency updates
python -m pip list --outdated
```

> **Tip**: Add `python scripts/generate_project_stats.py --markdown > docs/current_stats.md` to your CI/CD pipeline to automatically keep these metrics current.

## Quick Start

### Prerequisites
- Python 3.11+
- Azure Document Intelligence account (for extraction)
- Azure Storage account (optional, can use local storage)

### Installation

1. **Clone this repository**
   ```bash
   git clone <repository-url>
   cd FinDataExtractorVanilla
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure credentials
   ```

5. **Initialize database**
   ```bash
   alembic upgrade head
   ```

6. **Run the application**
   ```bash
   uvicorn api.main:app --reload
   ```

7. **Access API documentation**
   - Open: http://localhost:8000/docs

## Project Structure

```
FinDataExtractorVanilla/
├── README.md                 # This file
├── requirements.txt          # Simplified dependencies
├── .env.example              # Environment variable template
├── docker-compose.yml        # Simple Docker setup
├── Dockerfile                # Container configuration
├── src/                      # Core application code
│   ├── ingestion/            # PDF file ingestion
│   ├── extraction/           # Data extraction from invoices
│   ├── validation/           # Basic validation rules
│   ├── matching/             # Document matching
│   ├── models/               # Data models
│   └── config.py             # Simple configuration
├── api/                      # FastAPI application
│   ├── main.py              # Application entry point
│   └── routes/              # API route handlers
├── tests/                    # Test suite
└── docs/                     # Documentation
```

## Key Features

### 1. Invoice Ingestion
- Upload single or batch PDF invoices
- Automatic file validation
- Secure storage

### 2. Data Extraction
- Extract invoice number, date, amount, vendor
- Line item extraction
- Uses Azure Document Intelligence

### 3. Basic Validation
- Required field validation
- Format checks
- Business rule validation

### 4. Document Matching
- Match invoices to purchase orders
- Confidence scoring

## API Endpoints

- `POST /api/ingestion/upload` - Upload invoice PDFs
- `GET /api/extraction/{invoice_id}` - Get extracted data
- `POST /api/matching/match` - Match invoice to PO
- `GET /health` - Health check

See http://localhost:8000/docs for full API documentation.

## Configuration

See `.env.example` for required environment variables. Key settings:
- `AZURE_FORM_RECOGNIZER_ENDPOINT` - Azure Document Intelligence endpoint
- `AZURE_FORM_RECOGNIZER_KEY` - API key
- `DATABASE_URL` - Database connection string (SQLite for local dev)

## Documentation

- [Getting Started Guide](docs/GETTING_STARTED.md)
- [Azure Setup Guide](docs/AZURE_SETUP.md) - **Important: Read this for Azure resource decisions**
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Repository Relationship](docs/REPOSITORY_RELATIONSHIP.md)
- [Branch Strategy](docs/BRANCH_STRATEGY.md)

## Development

This project uses a `main`/`dev` branch strategy:
- **`main`** - Production-ready, stable code
- **`dev`** - Active development branch

For development work, use the `dev` branch:
```bash
git checkout dev
```

See [Branch Strategy](docs/BRANCH_STRATEGY.md) for details.

## Testing

The project includes a comprehensive test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit -v          # Unit tests only
pytest tests/integration -v  # Integration tests only
```

See [Testing Guide](docs/TESTING.md) for detailed testing documentation.

## Streamlit HITL Interface

A web-based interface for reviewing and validating extracted invoice data:

```bash
# Start the API server first
uvicorn api.main:app --reload

# Then start Streamlit (in a new terminal)
streamlit run streamlit_app.py
```

The interface provides:
- Field-level confidence scores with visual indicators
- PDF viewer for original invoices
- Line item review with confidence scores
- Validation submission workflow

See [Streamlit HITL Guide](docs/STREAMLIT_HITL.md) for detailed instructions.

## Azure Blob Storage Integration

The application can process invoices directly from Azure Blob Storage:

```bash
# Process a single invoice from Azure
python scripts/process_azure_invoices.py \
  --container invoices-raw \
  --blob-path "RAW Basic/invoice.pdf"

# Process batch from a specific path
python scripts/process_azure_invoices.py \
  --container invoices-raw \
  --prefix "RAW Basic/" \
  --max-files 10
```

**Features:**
-  Browse containers and blobs
-  Filter by path prefix (e.g., "RAW Basic/")
-  Download and process files
-  Complete end-to-end workflow

See [Azure Blob Processing Guide](docs/AZURE_BLOB_PROCESSING.md) for details.

## Demos

Interactive demos are available to showcase all features:

```bash
# Start the API server first
uvicorn api.main:app --reload

# Then run demos (in a new terminal)
cd demos
python demo_all_features.py  # Run complete workflow
# Or run individual demos:
python demo_01_ingestion.py    # Upload invoices
python demo_02_extraction.py   # Extract data
python demo_03_po_matching.py  # Match to PO
python demo_04_pdf_overlay.py # Generate overlay
python demo_05_hitl_review.py # Review & validate
python demo_06_erp_staging.py # Stage for ERP
```

See [Demo Guide](demos/DEMO_GUIDE.md) for detailed instructions and presentation tips.

## Planned Enhancements

See [GitHub Issues](.github/ISSUES.md) for planned enhancements:
- **Document Type Recognition** - Automatic document classification and routing
- **PO Data Integration** - Access PO data from separate storage for overlay
- **Approver List Integration** - Integrate approver registry for overlay display

For details, see [Overlay Enhancements](docs/OVERLAY_ENHANCEMENTS.md).

## License

[To be determined]

## Support

For issues or questions, please refer to the main [FinDataExtractor](../FinDataExtractor) project documentation or create an issue in this repository.

