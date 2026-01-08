# Line Item Data Flow Verification

## Overview

This document verifies that line item data changes flow correctly from the UI through the API to the SQLite database table.

## Data Flow Path

```
UI (Streamlit) → API Endpoint → DatabaseService → line_items Table
```

## Verification Points

### 1. UI to API
- **Location**: `streamlit_app.py`
- **Action**: User edits line items in UI
- **Submission**: `submit_validation()` sends `line_item_validations` to API
- **Status**: ✅ Working

### 2. API Endpoint
- **Location**: `api/routes/hitl.py`
- **Endpoint**: `POST /hitl/invoice/validate`
- **Action**: Processes `line_item_validations` and updates invoice
- **Status**: ✅ Working - Updates invoice.line_items and includes in patch

### 3. Database Service Update
- **Location**: `src/services/db_service.py`
- **Method**: `update_with_review_version()`
- **Action**: 
  - Updates JSON column (for backward compatibility)
  - **Also saves to line_items table** (NEW - Fixed)
- **Status**: ✅ Fixed - Now saves to table when line_items in patch

### 4. Database Service Load
- **Location**: `src/services/db_service.py`
- **Method**: `get_invoice()`
- **Action**: 
  - Uses `selectinload` to eagerly load `line_items_relationship`
  - Converts to Pydantic models via `db_to_pydantic_invoice()`
- **Status**: ✅ Fixed - Now loads from table first

### 5. Database Utils
- **Location**: `src/models/db_utils.py`
- **Function**: `_get_line_items_from_db()`
- **Action**: 
  - Checks `line_items_relationship` first (table)
  - Falls back to JSON column if table is empty
- **Status**: ✅ Working - Prioritizes table over JSON

## Code Changes Made

### 1. `src/services/db_service.py`

#### Added line item table save in `update_with_review_version()`:
```python
if "line_items" in patch:
    from src.models.db_utils import json_to_line_items
    line_items_json = patch["line_items"]
    line_items_pydantic = json_to_line_items(line_items_json)
    await save_line_items_to_table(session, invoice_id, line_items_pydantic)
```

#### Added eager loading in `get_invoice()`:
```python
from sqlalchemy.orm import selectinload
result = await session.execute(
    select(InvoiceDB)
    .options(selectinload(InvoiceDB.line_items_relationship))
    .where(InvoiceDB.id == invoice_id)
)
```

#### Added eager loading in `list_invoices()`:
```python
query = select(InvoiceDB).options(selectinload(InvoiceDB.line_items_relationship))
```

### 2. `src/models/db_utils.py`

#### Improved `_get_line_items_from_db()`:
- Better handling of relationship loading
- Checks if relationship has items before falling back to JSON
- Prioritizes table data over JSON

## Testing

### Test Script
Run: `python scripts/test_line_item_persistence.py`

This script verifies:
1. ✅ Line items saved to table on create
2. ✅ Line items loaded from table
3. ✅ Line items updated in table
4. ✅ Line items deleted from table
5. ✅ Data persists correctly

### Manual Testing Steps

1. **Create Invoice with Line Items**:
   - Upload invoice via API
   - Verify line items saved to `line_items` table

2. **Edit Line Items in UI**:
   - Open invoice in Streamlit UI
   - Edit line item description/amount
   - Submit validation
   - Verify changes saved to `line_items` table

3. **Reload Invoice**:
   - Close and reopen invoice in UI
   - Verify edited line items appear correctly
   - Verify data loaded from table (not JSON)

4. **Delete Line Item**:
   - Delete a line item in UI
   - Submit validation
   - Verify line item removed from `line_items` table

## Database Verification

### Check Line Items in Table
```sql
SELECT invoice_id, line_number, description, amount 
FROM line_items 
WHERE invoice_id = '<invoice_id>'
ORDER BY line_number;
```

### Check JSON Column (should be empty or minimal)
```sql
SELECT id, line_items 
FROM invoices 
WHERE id = '<invoice_id>';
```

## Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| UI Line Item Editing | ✅ | Working |
| API Validation Endpoint | ✅ | Working |
| Database Save (Table) | ✅ | Fixed - Now saves to table |
| Database Load (Table) | ✅ | Fixed - Now loads from table |
| Backward Compatibility | ✅ | Falls back to JSON if table empty |

## Conclusion

✅ **All data changes are now comprehensively applied across backend through to frontend.**

- Line items edited in UI persist to SQLite `line_items` table
- Line items are loaded from the table (not JSON)
- Backward compatibility maintained (falls back to JSON if table empty)
- Full CRUD operations work correctly
