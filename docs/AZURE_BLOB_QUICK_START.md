# Quick Start: Process Invoices from Azure Blob Storage

## Yes! The application CAN process invoices from Azure Blob Storage

The application has full support for:
-  Connecting to Azure Blob Storage
-  Browsing files in specific paths (like "RAW Basic/")
-  Downloading files from Azure
-  Running them through the complete end-to-end workflow

## Quick Example

### Process a single invoice from "RAW Basic" path:

```bash
python scripts/process_azure_invoices.py \
  --container invoices-raw \
  --blob-path "RAW Basic/invoice.pdf"
```

### Process all PDFs from "RAW Basic" path:

```bash
python scripts/process_azure_invoices.py \
  --container invoices-raw \
  --prefix "RAW Basic/" \
  --extension pdf \
  --max-files 10
```

## Using the API

### List files in a path:
```bash
curl "http://localhost:8000/api/azure-import/list-blobs?container_name=invoices-raw&prefix=RAW Basic/"
```

### Process a file:
```bash
curl -X POST "http://localhost:8000/api/azure-import/process-blob?container_name=invoices-raw&blob_name=RAW Basic/invoice.pdf"
```

## What Happens

1. **Download**: File is downloaded from Azure Blob Storage
2. **Ingest**: File is validated and stored
3. **Extract**: Data is extracted using Azure Document Intelligence
4. **Store**: Extracted data is saved to database
5. **Ready**: Invoice is ready for review!

## Configuration

Make sure your `.env` has:
```env
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=..."
```

See [Azure Blob Processing Guide](AZURE_BLOB_PROCESSING.md) for full documentation.

