# Fix tax field extraction and database persistence + test reorganization

## Summary

This PR fixes a critical issue where tax fields were extracted but not persisted to the database, causing null values in the UI. It also includes comprehensive test reorganization and documentation cleanup.

## Key Changes

### Critical Fix
- **Tax Field Database Persistence**: Fixed missing tax fields in `db_utils.py` conversion functions
  - Added `gst_amount`, `pst_amount`, `qst_amount`, `hst_amount` to `pydantic_to_db_invoice`
  - Added `gst_rate`, `pst_rate`, `qst_rate`, `hst_rate` to `pydantic_to_db_invoice`
  - Added all tax fields to `db_to_pydantic_invoice` for proper retrieval
  - Added other missing fields (vendor_email, customer_email, shipping_date, etc.)

### Repository Organization
- **Test Structure Reorganization**: Organized tests into DEMO/DEV/PROD categories
  - Created `tests/demo/` for standalone quick tests
  - Created `tests/dev/` for development tests with mocks
  - Created `tests/prod/` for production tests with real services
  - Organized by test pyramid (unit/integration/e2e)
- **Test Reports Organization**: Moved all reports to `tests/reports/`
- **Test Scripts Organization**: Moved scripts to `tests/scripts/`
- **Test Utilities Organization**: Moved utilities to `tests/utils/`

### Cleanup
- Removed temporary/intermediate documentation files
- Kept only test results and core documentation

## Impact

- **Before**: Tax fields were extracted but showed as null in UI due to missing database persistence
- **After**: Tax fields are properly saved to and retrieved from database, displaying correctly in UI

## Testing

- All existing tests pass
- Database conversion functions verified
- Test structure validated

## Files Changed

- `src/models/db_utils.py` - Added missing tax fields to conversion functions
- `tests/README.md` - Updated with new test structure
- 149 files total (5,478 insertions, 11,157 deletions)

## Next Steps

After merge, existing invoices will need to be re-extracted to populate tax fields in the database.
