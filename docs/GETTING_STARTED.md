# Getting Started with FinDataExtractor Vanilla

This guide will help you get started with the simplified FinDataExtractor Vanilla system.

## Prerequisites

- Python 3.11 or higher
- Azure Document Intelligence account (for invoice extraction)
- Azure Storage account (optional - can use local storage)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd FinDataExtractorVanilla
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
# Azure Document Intelligence (Required)
AZURE_FORM_RECOGNIZER_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=your-api-key-here
AZURE_FORM_RECOGNIZER_MODEL=prebuilt-invoice

# Database (SQLite for local development)
DATABASE_URL=sqlite+aiosqlite:///./findataextractor.db

# Storage (optional - uses local storage by default)
LOCAL_STORAGE_PATH=./storage
```

### 5. Initialize Database

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

### 6. Start the Application

```bash
uvicorn api.main:app --reload
```

The API will be available at: http://localhost:8000

### 7. Access API Documentation

Open your browser and navigate to:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Basic Usage

### Upload an Invoice

```bash
curl -X POST "http://localhost:8000/api/ingestion/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@path/to/invoice.pdf"
```

### Extract Data from Invoice

```bash
curl -X POST "http://localhost:8000/api/extraction/extract/{invoice_id}" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "file_identifier": "path/to/file",
    "file_name": "invoice.pdf"
  }'
```

## Project Structure

```
FinDataExtractorVanilla/
├── api/                    # FastAPI application
│   ├── main.py            # Application entry point
│   └── routes/            # API route handlers
├── src/                    # Core application code
│   ├── ingestion/         # PDF file ingestion
│   ├── extraction/        # Data extraction
│   ├── matching/          # Document matching
│   ├── models/            # Data models
│   └── config.py          # Configuration
├── docs/                   # Documentation
├── alembic/               # Database migrations
└── requirements.txt       # Python dependencies
```

## Next Steps

- Review the [Architecture Overview](ARCHITECTURE.md)
- Check the [API Reference](API_REFERENCE.md)
- See the [Repository Relationship Guide](../README.md#relationship-to-full-version)

## Troubleshooting

### Common Issues

1. **Azure Document Intelligence errors**
   - Verify your endpoint and API key are correct
   - Check that your Azure subscription is active

2. **Database connection errors**
   - Ensure the database file path is writable
   - For SQLite, check file permissions

3. **File upload errors**
   - Verify file size is under 50MB
   - Ensure file is a valid PDF

## Support

For more information, see the main [README](../README.md) or refer to the full [FinDataExtractor](../FinDataExtractor) project documentation.

