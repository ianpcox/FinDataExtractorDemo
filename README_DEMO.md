# FinDataExtractorDEMO

## Overview

This is a **separate demo project** created from FinDataExtractorVanilla for demonstration purposes. All demo-specific modifications are contained here, keeping the original FinDataExtractorVanilla project untouched.

## Purpose

This demo project includes:
- Mock Azure Document Intelligence client (no Azure required)
- Demo mode configuration
- Sample invoice data pre-population
- Optimized performance for quick demos (< 5 second extraction)
- All demo-specific documentation

## Quick Start

```powershell
# Run setup (copies invoices from FinDataExtractor/data)
python scripts/setup_demo.py

# Start demo
.\scripts\start_demo.ps1
```

**Invoice Source:** All demo invoices are sourced from the local `data/sample_invoices/Raw/Raw_Basic/` folder (copied from FinDataExtractor/data)

## Relationship to Main Project

- **FinDataExtractorVanilla**: Production-ready project (untouched)
- **FinDataExtractorDEMO**: Demo-only project (all demo changes here)

## Key Differences from Main Project

1. **Mock Azure Services**: Uses mock clients instead of real Azure APIs
2. **Demo Database**: Separate database with pre-populated sample invoices
3. **Performance Optimized**: LLM fallback disabled, synchronous operations
4. **Demo Documentation**: All demo guides and setup scripts

## Files Added/Modified for Demo

- `src/extraction/mock_document_intelligence_client.py` - Mock Azure client
- `src/config.py` - Added DEMO_MODE setting
- `src/extraction/extraction_service.py` - Demo mode optimizations
- `src/extraction/document_intelligence_client.py` - Auto-uses mock in demo mode
- `scripts/setup_demo.py` - Demo database setup (sources from `FinDataExtractor/data`)
- `scripts/start_demo.ps1` - Demo startup script
- `streamlit_app.py` - Fixed confidence value type handling

## Invoice Source

All demo invoices are sourced from the local `data/` folder:
```
data/sample_invoices/Raw/Raw_Basic/
```

The `data/` folder is copied from `FinDataExtractor/data` to keep the demo project self-contained.

The `setup_demo.py` script automatically:
1. Copies PDF files from `data/sample_invoices/Raw/Raw_Basic/`
2. Places them in `storage/raw/` for the demo
3. Creates database records linked to these files

## Usage

```bash
# Start demo mode
.\scripts\start_demo.ps1  # Windows
./scripts/start_demo.sh   # Linux/Mac
```

Access:
- Streamlit UI: http://localhost:8501
- API Server: http://localhost:8000

---

**Note**: This project is for demonstration only. For production use, use FinDataExtractorVanilla.

