# FinDataExtractor Vanilla - Simplified Invoice Processing

## Overview

**FinDataExtractor Vanilla** is a simplified, easy-to-use version of the FinDataExtractor system designed for CATSA users who need core invoice processing capabilities without the complexity of advanced features.

This version focuses on:
- ✅ **Simple PDF invoice ingestion**
- ✅ **Core data extraction** (invoice number, date, amount, vendor, line items)
- ✅ **Basic validation** (format checks, required fields)
- ✅ **Document matching** (invoice to PO matching)
- ✅ **Straightforward API** (no versioning complexity)
- ✅ **Easy setup** (minimal configuration)

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
- [API Reference](docs/API_REFERENCE.md)
- [Architecture Overview](docs/ARCHITECTURE.md)

## License

[To be determined]

## Support

For issues or questions, please refer to the main [FinDataExtractor](../FinDataExtractor) project documentation or create an issue in this repository.

