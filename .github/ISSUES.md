# GitHub Issues for FinDataExtractorVanilla

This document lists the GitHub issues that should be created for the overlay renderer enhancements and related features.

## Overlay Renderer Enhancements

### Issue #1: Overlay Renderer - Approver List Integration
**File**: `.github/ISSUE_TEMPLATE/overlay-approver-integration.md`

**Summary**: Enhance the PDF overlay renderer to pull approver information from an approver code list/registry instead of only using the invoice's stored approver fields.

**Labels**: `enhancement`, `overlay`, `medium-priority`

---

### Issue #2: Overlay Renderer - PO Data Integration
**File**: `.github/ISSUE_TEMPLATE/overlay-po-integration.md`

**Summary**: Enhance the PDF overlay renderer to pull Purchase Order (PO) data from a separate PO database/storage system to display matched PO information on the invoice overlay.

**Labels**: `enhancement`, `overlay`, `high-priority`, `po-integration`

---

## Document Management Enhancements

### Issue #3: Document Type Recognition and Separate Storage
**File**: `.github/ISSUE_TEMPLATE/document-type-recognition.md`

**Summary**: Implement document type recognition to automatically classify uploaded documents (Invoice, PO, Receipt, etc.) and route them to appropriate storage containers and databases.

**Labels**: `enhancement`, `document-recognition`, `high-priority`, `architecture`

---

## How to Create These Issues

1. Go to the GitHub repository: `https://github.com/ianpcox/FinDataExtractorVanilla`
2. Click "Issues" → "New Issue"
3. Copy the content from each template file
4. Paste into the issue description
5. Add appropriate labels
6. Set milestone if applicable

## Front-End UI Issues

### Issue #4: Front-End UI Design and Architecture
**File**: `.github/ISSUE_TEMPLATE/frontend-ui-design.md`

**Summary**: Design and implement a front-end user interface to complement the FinDataExtractorVanilla API. Includes UI technology selection, core features, and design considerations.

**Labels**: `enhancement`, `frontend`, `ui-design`, `high-priority`

---

### Issue #5: Streamlit HITL UI Implementation
**File**: `.github/ISSUE_TEMPLATE/streamlit-hitl-ui.md`

**Summary**: Implement a Streamlit-based Human-in-the-Loop (HITL) user interface for invoice validation and approval. Quick-to-implement Python-based UI.

**Labels**: `enhancement`, `frontend`, `streamlit`, `hitl`, `high-priority`

---

### Issue #6: React-Based Front-End UI Implementation
**File**: `.github/ISSUE_TEMPLATE/react-ui-implementation.md`

**Summary**: Implement a modern React-based front-end application for production-grade, scalable UI solution.

**Labels**: `enhancement`, `frontend`, `react`, `typescript`, `medium-priority`

---

## Issue Dependencies

```
Issue #3 (Document Type Recognition)
    ↓
Issue #2 (PO Data Integration)
    ↓
Issue #1 (Approver List Integration)

Issue #4 (Front-End UI Design) - Can be done in parallel
    ↓
Issue #5 (Streamlit UI) OR Issue #6 (React UI) - Choose one
```

