# Feature: Overlay Renderer - PO Data Integration

## Description
Enhance the PDF overlay renderer to pull Purchase Order (PO) data from a separate PO database/storage system to display matched PO information on the invoice overlay.

## Current State
The overlay renderer currently only displays PO number from the invoice (`invoice.po_number`) without additional PO context like PO date, PO total, line item matching, or commitment status.

## Requirements

### 1. PO Data Access
- Access PO data from separate PO database/storage
- Support querying PO by PO number
- Retrieve PO header information (date, vendor, total, status)
- Retrieve PO line items for comparison/validation

### 2. Enhanced Overlay Display
- Display matched PO information in overlay (PO number, date, total)
- Show PO status (approved, committed, etc.)
- Display PO line item summary or matching status
- Highlight discrepancies between invoice and PO (amounts, line items)

### 3. Integration Architecture
- **Option A**: Direct database connection to PO database
- **Option B**: PO service/API integration
- **Option C**: PO data sync/cache in invoice database
- Consider: Separate storage containers for PO documents

### 4. PO Matching Context
- Show which invoice line items match PO line items
- Display PO commitment/budget information
- Show Section 32 approval status if applicable

## Acceptance Criteria
- [ ] PO data is accessible from separate storage/database
- [ ] Overlay displays matched PO information (number, date, total)
- [ ] Overlay shows PO status and commitment information
- [ ] PO line item matching is displayed or indicated
- [ ] Graceful handling when PO is not found or not matched
- [ ] Documentation updated with PO integration architecture

## Technical Considerations
- PO database may be in different location/region
- Consider caching PO data for performance
- Handle PO updates/versioning
- Support multiple PO numbers per invoice
- Consider PO document storage (separate from invoices)

## Related Issues
- See issue: Document Type Recognition and Separate Storage
- See issue: Approver List Integration
- See issue: PO Matching Service (if not already implemented)

## Priority
High - PO information is critical for invoice approval workflow

