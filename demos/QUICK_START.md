# Quick Start Guide - Running Demos

## Prerequisites

1. **API Server Running**
   ```bash
   cd FinDataExtractorVanilla
   .\venv\Scripts\Activate.ps1  # Windows
   uvicorn api.main:app --reload
   ```

2. **Sample Invoice PDF**
   - Place at least one invoice PDF in `demos/sample_data/`
   - Any valid PDF invoice will work

## Running Demos

### Option 1: Complete Workflow (Recommended for First Demo)

```bash
cd demos
python demo_all_features.py
```

This runs all 6 demos in sequence showing the complete workflow.

### Option 2: Individual Demos

Run each demo individually:

```bash
cd demos

# 1. Upload invoice
python demo_01_ingestion.py

# 2. Extract data (use invoice_id from step 1)
python demo_02_extraction.py

# 3. Match to PO
python demo_03_po_matching.py

# 4. Generate PDF overlay
python demo_04_pdf_overlay.py

# 5. Review & validate
python demo_05_hitl_review.py

# 6. Stage for ERP
python demo_06_erp_staging.py
```

## Expected Output

Each demo will:
- ✅ Show progress and results
- ✅ Display extracted data
- ✅ Save output files to `demos/output/`
- ✅ Provide next steps

## Troubleshooting

**API Connection Error:**
- Make sure API server is running on `http://localhost:8000`
- Check `uvicorn api.main:app --reload` is running

**No PDF Files Found:**
- Place sample invoice PDFs in `demos/sample_data/`
- Check file has `.pdf` extension

**Import Errors:**
- Make sure you're in the `demos` directory
- Check virtual environment is activated

## Presentation Tips

1. **Start with complete workflow** (`demo_all_features.py`)
2. **Then show individual features** for detailed explanation
3. **Open generated files** to show visual results
4. **Highlight confidence scores** - shows quality assurance
5. **Show API docs** at `http://localhost:8000/docs`

