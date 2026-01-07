# Feature: Streamlit HITL UI Implementation

## Description
Implement a Streamlit-based Human-in-the-Loop (HITL) user interface for invoice validation and approval. This provides a quick-to-implement Python-based UI that integrates seamlessly with the FastAPI backend.

## Current State
-  HITL API endpoints implemented (`/api/hitl/*`)
-  Field-level confidence scores available
-  PDF retrieval endpoint available
-  No UI for users to interact with

## Requirements

### 1. Streamlit Application Structure
```
streamlit_app/
├── main.py              # Main Streamlit app
├── pages/
│   ├── dashboard.py    # Invoice list/dashboard
│   ├── validation.py   # HITL validation interface
│   ├── approval.py     # Approval workflow
│   └── matching.py     # PO matching interface
├── components/
│   ├── invoice_card.py
│   ├── confidence_indicator.py
│   ├── pdf_viewer.py
│   └── field_editor.py
└── utils/
    ├── api_client.py
    └── formatters.py
```

### 2. Core Pages

#### 2.1 Dashboard Page (`pages/dashboard.py`)
- Invoice list with filters
- Status indicators
- Quick actions (validate, approve, reject)
- Statistics/overview
- Search and pagination

#### 2.2 Validation Page (`pages/validation.py`)
- Side-by-side layout: PDF viewer | Data form
- Field-level confidence indicators
- Inline editing for corrections
- Validation checklist
- Save/submit validation

#### 2.3 Approval Page (`pages/approval.py`)
- BV approval interface
- FA approval interface
- Approval history
- Bulk approval actions
- Rejection workflow

#### 2.4 Matching Page (`pages/matching.py`)
- PO matching results
- Manual PO selection
- Match confidence display
- PO details view

### 3. UI Components

#### 3.1 Confidence Indicator
- Visual representation of confidence score
- Color coding (red/yellow/green)
- Tooltip with exact score
- Per-field indicators

#### 3.2 PDF Viewer
- Embedded PDF display
- Zoom controls
- Page navigation
- Download button

#### 3.3 Field Editor
- Inline editing
- Validation feedback
- Confidence display
- Correction history

#### 3.4 Invoice Card
- Summary information
- Status badge
- Quick actions
- Confidence indicator

### 4. Features

#### 4.1 Invoice List
- Display invoices with key fields
- Filter by status, date, vendor
- Sort by various criteria
- Search functionality
- Pagination

#### 4.2 Validation Interface
- Load invoice data from API
- Display PDF alongside form
- Show confidence per field
- Allow corrections
- Submit validation

#### 4.3 Approval Workflow
- BV approval step
- FA approval step
- Notes/comments
- Rejection with reasons
- Audit trail

## Technical Implementation

### API Client
```python
# utils/api_client.py
class APIClient:
    def get_invoice(self, invoice_id: str)
    def validate_invoice(self, invoice_id: str, validations: dict)
    def get_invoice_pdf(self, invoice_id: str)
    def list_invoices(self, filters: dict)
    # ... other methods
```

### State Management
- Use Streamlit session state
- Cache API responses
- Handle loading states
- Error handling

### Dependencies
```txt
streamlit>=1.28.0
requests>=2.31.0
pypdf2>=3.0.0  # For PDF handling
pillow>=10.0.0  # For image handling
```

## Acceptance Criteria
- [ ] Streamlit app structure created
- [ ] Dashboard page implemented
- [ ] Validation page with PDF viewer implemented
- [ ] Approval workflow pages implemented
- [ ] Confidence indicators displayed
- [ ] API integration working
- [ ] Error handling implemented
- [ ] Responsive layout verified
- [ ] User testing completed

## Design Mockups

### Validation Page Layout
```
┌─────────────────────────────────────────────────┐
│  Invoice Validation - INV-12345                 │
├──────────────────┬─────────────────────────────┤
│                  │  Invoice Number: INV-12345   │
│                  │  Confidence: [████░░] 85%   │
│   PDF Viewer     │                              │
│   [Zoom] [Pages] │  Invoice Date: 2024-01-15   │
│                  │  Confidence: [█████░] 95%    │
│   [PDF Content]  │                              │
│                  │  Vendor: Acme Corp           │
│                  │  Confidence: [███░░░] 60%   │
│                  │  [Edit]                      │
│                  │                              │
│                  │  Line Items:                 │
│                  │  1. Item A - $100.00         │
│                  │     Confidence: [█████░] 90% │
│                  │                              │
│                  │  [Validate All] [Save]        │
└──────────────────┴─────────────────────────────┘
```

## Related Issues
- See issue: Front-End UI Design and Architecture
- See issue: HITL API Endpoints (prerequisite)

## Priority
High - Streamlit provides quick implementation path

## Notes
- Streamlit is Python-based, easy to integrate with existing codebase
- Good for internal tools and quick prototyping
- Can be deployed easily (Streamlit Cloud, Docker)
- May need additional framework for production-grade UI

