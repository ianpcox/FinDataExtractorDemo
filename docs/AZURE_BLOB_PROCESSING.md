# Azure Blob Storage Processing

## Overview

The application can connect to Azure Blob Storage, browse files in specific paths (like "RAW Basic"), and process them through the complete end-to-end workflow.

## Features

- **Browse Azure Storage**: List containers and blobs with path filtering
- **Download from Paths**: Download files from specific paths like "RAW Basic/" or "Raw_Basic/"
- **End-to-End Processing**: Automatically run ingestion → extraction → database storage
- **Batch Processing**: Process multiple files at once

## Configuration

Ensure your `.env` file has Azure Storage credentials:

```env
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=..."
# OR
AZURE_STORAGE_ACCOUNT_NAME="your-storage-account"
```

## Usage

### Option 1: Using the API

#### List Containers
```bash
GET /api/azure-import/list-containers
```

#### List Blobs in a Path
```bash
GET /api/azure-import/list-blobs?container_name=invoices-raw&prefix=RAW Basic/
```

#### Process Single File
```bash
POST /api/azure-import/process-blob?container_name=invoices-raw&blob_name=RAW Basic/invoice.pdf
```

#### Process Batch
```bash
POST /api/azure-import/process-batch?container_name=invoices-raw&prefix=RAW Basic/&max_files=10
```

### Option 2: Using the Script

#### Process Single File
```bash
python scripts/process_azure_invoices.py \
  --container invoices-raw \
  --blob-path "RAW Basic/invoice.pdf"
```

#### Process Batch from Path
```bash
python scripts/process_azure_invoices.py \
  --container invoices-raw \
  --prefix "RAW Basic/" \
  --extension pdf \
  --max-files 10
```

#### Skip Extraction (Ingestion Only)
```bash
python scripts/process_azure_invoices.py \
  --container invoices-raw \
  --prefix "RAW Basic/" \
  --no-extraction
```

## Examples

### Example 1: Process Single Invoice from "RAW Basic" Path

```bash
# Using API
curl -X POST "http://localhost:8000/api/azure-import/process-blob?container_name=invoices-raw&blob_name=RAW Basic/invoice_001.pdf"

# Using Script
python scripts/process_azure_invoices.py \
  --container invoices-raw \
  --blob-path "RAW Basic/invoice_001.pdf"
```

### Example 2: Process All PDFs from "RAW Basic" Path

```bash
# Using API
curl -X POST "http://localhost:8000/api/azure-import/process-batch?container_name=invoices-raw&prefix=RAW Basic/&file_extension=pdf&max_files=50"

# Using Script
python scripts/process_azure_invoices.py \
  --container invoices-raw \
  --prefix "RAW Basic/" \
  --extension pdf \
  --max-files 50
```

### Example 3: List Files in a Path

```bash
# Using API
curl "http://localhost:8000/api/azure-import/list-blobs?container_name=invoices-raw&prefix=RAW Basic/&file_extension=pdf"

# Response shows all PDFs in that path
```

## Workflow

When processing a file from Azure:

1. **Download**: File is downloaded from Azure Blob Storage
2. **Ingest**: File is validated and stored (back to Azure or locally)
3. **Extract**: Data is extracted using Azure Document Intelligence
4. **Store**: Extracted data is saved to database
5. **Ready**: Invoice is ready for review in Streamlit or HITL API

## Path Handling

Azure Blob Storage paths can be specified in different formats:

- `RAW Basic/invoice.pdf` - Forward slash separator
- `Raw_Basic/invoice.pdf` - Underscore separator
- `RAW Basic/subfolder/invoice.pdf` - Nested paths

The `prefix` parameter filters blobs that start with the given path.

## Error Handling

- **Connection Errors**: Check Azure credentials and network connectivity
- **Blob Not Found**: Verify container name and blob path
- **Processing Errors**: Check logs for detailed error messages

## Integration with Existing Workflow

Files processed from Azure follow the same workflow as uploaded files:

- Same database schema
- Same extraction process
- Same HITL review interface
- Same ERP staging capabilities

## API Documentation

Full API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Look for the "azure-import" tag for all Azure import endpoints.

