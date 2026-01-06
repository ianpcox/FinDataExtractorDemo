# Sample Invoice Data

This directory contains sample invoice files for testing and development.

## Directory Structure

```
sample_invoices/
├── Raw/                    # Raw invoice PDFs (extracted from zip files)
│   ├── Raw_Basic/          # 47 basic invoice samples
│   ├── Raw_Screeners_Sanitization/  # Sanitization service invoices
│   └── Raw_Screeners_Travel/       # Travel-related invoices
├── Markedup/               # Marked-up invoices (for validation/testing)
│   ├── Markedup_Basic/     # Marked-up basic invoices
│   ├── Markedup_Screeners_Sanitizations/  # Marked-up sanitization invoices
│   ├── Markedup_Screeners_Travel/   # Marked-up travel invoices
│   └── *.zip               # Original marked-up zip archives
└── *.zip                   # Original raw zip files (archived)
```

## Files

### Raw Invoices
- **Raw_Basic/** - 47 basic invoice PDF samples
- **Raw_Screeners_Sanitization/** - Sanitization service invoices (PDFs and support images)
- **Raw_Screeners_Travel/** - Travel-related invoices

### Marked-up Invoices (for validation/testing)
- **Markedup_Basic/** - Marked-up versions of basic invoices
- **Markedup_Screeners_Sanitizations/** - Marked-up sanitization invoices
- **Markedup_Screeners_Travel/** - Marked-up travel invoices

### Original Archives
- **Raw_Basic.zip** - Original raw zip archive
- **Raw_Screeners_Sanitization.zip** - Original raw zip archive
- **Raw_Screeners_Travel.zip** - Original raw zip archive
- **Markedup_Basic1-6.zip** - Marked-up basic invoice archives (in Markedup folder)
- **Markedup_Screeners_Sanitizations.zip** - Marked-up sanitization archive (in Markedup folder)
- **Markedup_Screeners_Travel.zip** - Marked-up travel archive (in Markedup folder)

## Usage

These files contain sample invoices that can be used for:
- Testing the extraction pipeline
- Training/validating Document Intelligence models
- Development and debugging
- Performance testing
- Comparing extraction results with marked-up versions

## Uploading to Azure Blob Storage

To upload raw invoices to your Azure Blob Storage for testing:

```bash
# Using Azure CLI - Upload all PDFs from Raw folder
az storage blob upload-batch \
  --source data/sample_invoices/Raw/ \
  --destination invoices-raw \
  --account-name sadiofindataextractcace \
  --auth-mode login \
  --pattern "*.pdf"
```

Or use the ingestion API:

```python
from scripts.test_ingestion import upload_invoice
import os

# Upload individual PDFs from Raw folder
raw_folder = "data/sample_invoices/Raw"
for root, dirs, files in os.walk(raw_folder):
    for file in files:
        if file.endswith('.pdf'):
            file_path = os.path.join(root, file)
            upload_invoice(file_path)
```

## Note

These are sample files provided by the client. They should be:
- Kept secure (not publicly accessible)
- Used only for development/testing
- Replaced with production data when available

