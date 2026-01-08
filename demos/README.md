# Demo Guide - FinDataExtractor Vanilla

## Quick Start

1. **Start the API server:**
   ```bash
   cd FinDataExtractorVanilla
   .\venv\Scripts\Activate.ps1  # Windows
   # or: source venv/bin/activate  # Linux/Mac
   
   uvicorn api.main:app --reload
   ```

2. **Run demos** (in a new terminal):
   ```bash
   cd FinDataExtractorVanilla/demos
   python demo_01_ingestion.py
   python demo_02_extraction.py
   # ... etc
   ```

## Demo Scripts

1. **`demo_01_ingestion.py`** - Upload invoice PDFs
2. **`demo_02_extraction.py`** - Extract data from invoices
3. **`demo_03_po_matching.py`** - Match invoices to purchase orders
4. **`demo_04_pdf_overlay.py`** - Generate PDF with overlay
5. **`demo_05_hitl_review.py`** - Review and validate invoices
6. **`demo_06_erp_staging.py`** - Format invoices for ERP systems
7. **`demo_all_features.py`** - Run all demos in sequence

## Prerequisites

- API server running on `http://localhost:8000`
- Azure Document Intelligence configured (for extraction)
- Sample PDF invoice file (see `sample_invoice.pdf`)

## Sample Data

Place sample invoice PDFs in `demos/sample_data/` directory.

See [DEMO_GUIDE.md](./DEMO_GUIDE.md) for detailed instructions.

