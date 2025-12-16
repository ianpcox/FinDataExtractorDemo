# Complete Demo Guide - FinDataExtractor Vanilla

This guide walks you through demonstrating each feature of the FinDataExtractor Vanilla system to stakeholders.

## Prerequisites

### 1. Start the API Server

```bash
# Activate virtual environment
cd FinDataExtractorVanilla
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# or: source venv/bin/activate  # Linux/Mac

# Start the server
uvicorn api.main:app --reload
```

The API will be available at: `http://localhost:8000`
API Documentation: `http://localhost:8000/docs`

### 2. Verify Configuration

Ensure your `.env` file has:
- `AZURE_FORM_RECOGNIZER_ENDPOINT` - Document Intelligence endpoint
- `AZURE_FORM_RECOGNIZER_KEY` - Document Intelligence API key
- `DATABASE_URL` - Database connection (SQLite default)

### 3. Prepare Sample Data

Place sample invoice PDFs in `demos/sample_data/` directory.

---

## Demo 1: Invoice Ingestion

**Purpose:** Demonstrate uploading invoice PDFs to the system.

**What it shows:**
- Upload single invoice PDF
- Upload multiple invoices (batch)
- File validation
- Storage confirmation

**Run:**
```bash
python demos/demo_01_ingestion.py
```

**Expected Output:**
- Invoice ID assigned
- File stored successfully
- File metadata (size, pages, etc.)

**Talking Points:**
- "We can upload invoices via API"
- "System validates PDF format automatically"
- "Each invoice gets a unique ID for tracking"
- "Supports batch uploads for efficiency"

---

## Demo 2: Invoice Extraction

**Purpose:** Demonstrate extracting structured data from invoice PDFs using Azure Document Intelligence.

**What it shows:**
- Automatic field extraction (invoice number, date, vendor, amounts)
- Line item extraction
- Confidence scores per field
- Subtype detection (ShiftService, PerDiemTravel)

**Run:**
```bash
python demos/demo_02_extraction.py
```

**Expected Output:**
- Extracted invoice data (JSON)
- Field-level confidence scores
- Line items with details
- Overall extraction confidence

**Talking Points:**
- "Uses Azure Document Intelligence for accurate extraction"
- "Extracts all key fields automatically"
- "Provides confidence scores for quality assurance"
- "Detects invoice subtypes for specialized processing"

---

## Demo 3: PO Matching

**Purpose:** Demonstrate matching invoices to purchase orders.

**What it shows:**
- Match invoice to PO by number
- Fuzzy matching when PO number doesn't match exactly
- Confidence scoring
- Match details (vendor, amount, dates)

**Run:**
```bash
python demos/demo_03_po_matching.py
```

**Expected Output:**
- Match result with confidence score
- Matched PO details
- Match strategy used (exact, fuzzy, hybrid)
- Validation results

**Talking Points:**
- "Automatically matches invoices to purchase orders"
- "Multiple matching strategies for flexibility"
- "Confidence scores help identify potential issues"
- "Validates amounts and dates for accuracy"

---

## Demo 4: PDF Overlay

**Purpose:** Demonstrate adding visual overlay to invoice PDFs with extracted data and approval information.

**What it shows:**
- Original PDF with overlay
- Invoice header information
- Financial coding (red box)
- Approval status and approvers

**Run:**
```bash
python demos/demo_04_pdf_overlay.py
```

**Expected Output:**
- New PDF file with overlay
- Visual boxes showing:
  - Invoice summary (top)
  - Financial coding (red box)
  - Approval information (bottom)

**Talking Points:**
- "Adds visual information to original PDF"
- "Shows extracted data for quick review"
- "Highlights financial coding for approvers"
- "Tracks approval workflow"

---

## Demo 5: HITL (Human-in-the-Loop) Review

**Purpose:** Demonstrate reviewing and validating extracted invoice data.

**What it shows:**
- View invoice with field-level confidence
- Review low-confidence fields
- Validate/correct extracted data
- View original PDF

**Run:**
```bash
python demos/demo_05_hitl_review.py
```

**Expected Output:**
- Invoice data with confidence scores
- Fields flagged for review
- Ability to update values
- Validation status

**Talking Points:**
- "Review interface for quality assurance"
- "Highlights fields with low confidence"
- "Allows manual correction when needed"
- "Tracks who validated and when"

---

## Demo 6: ERP Staging

**Purpose:** Demonstrate formatting approved invoices for ERP system integration.

**What it shows:**
- Format invoice data for ERP
- Multiple output formats (JSON, CSV, XML, Dynamics GP)
- Tax breakdown
- Approval metadata

**Run:**
```bash
python demos/demo_06_erp_staging.py
```

**Expected Output:**
- ERP-ready payload in selected format
- Formatted for MS Dynamics Great Plains
- Includes all required fields
- Ready for import

**Talking Points:**
- "Formats data for ERP integration"
- "Supports multiple ERP systems"
- "Includes all required fields and metadata"
- "Ready for automated import"

---

## Demo 7: Complete Workflow

**Purpose:** Demonstrate the complete end-to-end workflow.

**Run:**
```bash
python demos/demo_all_features.py
```

**What it shows:**
- Complete workflow from upload to ERP staging
- All features working together
- Real-world scenario

**Talking Points:**
- "Complete automated workflow"
- "From PDF upload to ERP-ready data"
- "Minimal manual intervention required"
- "Audit trail throughout"

---

## Troubleshooting

### API Server Not Starting
- Check if port 8000 is available
- Verify virtual environment is activated
- Check `.env` file exists

### Azure Document Intelligence Errors
- Verify credentials in `.env`
- Check endpoint URL is correct
- Ensure API key is valid

### Database Errors
- Run `alembic upgrade head` to create tables
- Check `DATABASE_URL` in `.env`

### PDF Not Found
- Ensure sample PDFs are in `demos/sample_data/`
- Check file paths in demo scripts

---

## Presentation Tips

1. **Start with Demo 7** (complete workflow) for overview
2. **Then dive into individual features** (Demos 1-6)
3. **Show API documentation** at `http://localhost:8000/docs`
4. **Highlight confidence scores** - shows quality assurance
5. **Emphasize automation** - reduces manual work
6. **Show error handling** - system is robust

---

## Next Steps

After the demo, discuss:
- Integration requirements
- Customization needs
- Deployment options
- Training requirements

