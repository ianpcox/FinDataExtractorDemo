# Streamlit HITL Interface

## Overview

The Streamlit HITL (Human-in-the-Loop) interface provides a web-based UI for reviewing and validating extracted invoice data. It displays field-level confidence scores, allows corrections, and submits validations back to the API.

## Features

- **Invoice List View**: Browse and filter invoices by status
- **Field-Level Review**: See all extracted fields with confidence scores
- **Line Item Review**: Review individual line items with confidence
- **PDF Viewer**: View original invoice PDF inline
- **Validation Submission**: Submit corrections and validation status
- **Confidence Indicators**: Visual indicators for field confidence levels

## Running the Interface

### Prerequisites

1. **API Server Running**
   ```bash
   cd FinDataExtractorVanilla
   .\venv\Scripts\Activate.ps1  # Windows
   uvicorn api.main:app --reload
   ```

2. **Install Streamlit** (if not already installed)
   ```bash
   pip install streamlit
   ```

### Start Streamlit App

```bash
cd FinDataExtractorVanilla
streamlit run streamlit_app.py
```

The interface will open in your browser at `http://localhost:8501`

## Usage

### 1. Select Invoice

- Use the sidebar to filter invoices by status
- Select an invoice from the dropdown list
- Click "Refresh Invoice List" to reload

### 2. Review Fields

Navigate through tabs:

- **Fields Tab**: Review all extracted fields with confidence scores
  - Green (≥90%): High confidence - verified
  - Yellow (70-89%): Medium confidence - review recommended
  - Red (<70%): Low confidence - correction required

- **Line Items Tab**: Review line items
  - See summary table
  - Expand individual items for details
  - Check confidence scores

- **PDF Tab**: View original invoice PDF
  - Inline PDF viewer
  - Download option

- **Validation Tab**: Submit validation
  - Enter reviewer name
  - Select validation status
  - Add notes
  - Submit validation

### 3. Confidence Levels

- ** High (≥90%)**: Field extracted with high confidence - likely correct
- ** Medium (70-89%)**: Field extracted with medium confidence - review recommended
- ** Low (<70%)**: Field extracted with low confidence - correction likely needed

## Configuration

### API URL

The default API URL is `http://localhost:8000`. To change it, edit `streamlit_app.py`:

```python
API_BASE_URL = "http://your-api-url:8000"
```

### Customization

You can customize the interface by modifying:
- Colors and styling in the CSS section
- Field groupings in the Fields tab
- Display format for different data types

## Troubleshooting

### Cannot Connect to API

- Ensure API server is running on `http://localhost:8000`
- Check API_BASE_URL in `streamlit_app.py`
- Verify API endpoints are accessible

### No Invoices Displayed

- Upload invoices using the API or demo scripts
- Check status filter in sidebar
- Verify database has invoice records

### PDF Not Loading

- Check invoice file_path in database
- Verify file exists in storage
- Check file_handler configuration

## Integration with API

The Streamlit app uses these API endpoints:

- `GET /api/hitl/invoices` - List invoices
- `GET /api/hitl/invoice/{invoice_id}` - Get invoice details
- `GET /api/hitl/invoice/{invoice_id}/pdf` - Get invoice PDF
- `POST /api/hitl/invoice/validate` - Submit validation

## Next Steps

- Add field editing capabilities
- Implement bulk validation
- Add export functionality
- Integrate with approval workflow

