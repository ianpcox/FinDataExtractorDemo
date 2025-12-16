# Test Failures Summary

## Current Status
- **Total Tests**: 39
- **Passing**: 34
- **Failing**: 5

## Failing Tests

### 1. `test_complete_workflow` (integration/test_end_to_end.py)
**Issue**: Invoice status is "processing" instead of "extracted" after extraction
**Root Cause**: Status update in database not persisting correctly
**Fix Needed**: Ensure status field is properly updated when saving extracted invoice

### 2. `test_extract_invoice_with_addresses` (unit/test_field_extractor.py)
**Issue**: Address extraction not working - street is empty
**Root Cause**: Address mapping not handling test data format
**Fix Needed**: Update `_map_address` to handle "street" key in addition to "street_address"

### 3. `test_extract_invoice_field_confidence` (unit/test_field_extractor.py)
**Issue**: Field confidence values don't match expected
**Root Cause**: Field confidence mapping from Document Intelligence format
**Fix Needed**: Update `_extract_field_confidence` to properly map capitalized keys

### 4. `test_ingest_invoice_success` (unit/test_ingestion_service.py)
**Issue**: Status is "error" instead of "uploaded"
**Root Cause**: Database table not created in test session
**Fix Needed**: Ensure database tables are created before test runs

### 5. `test_extract_billing_period` (unit/test_subtype_extractors.py)
**Issue**: Billing period extraction returns None
**Root Cause**: Regex pattern doesn't match ISO date format (YYYY-MM-DD)
**Fix Needed**: Update `_extract_billing_period` regex to handle ISO dates

## Quick Fixes Applied

1. ✅ Added `pytest-timeout` with 45-second SLA
2. ✅ Added `pytest-xdist` for parallel execution
3. ✅ Updated pytest.ini with timeout configuration
4. ✅ Created fast test runner script

## Running Tests

### Fast Mode (stops on first failure):
```powershell
.\scripts\run_tests_with_progress.ps1 -Fast
```

### Full Mode (all tests with coverage):
```powershell
.\scripts\run_tests_with_progress.ps1
```

### Direct pytest:
```powershell
.\venv\Scripts\Activate.ps1
pytest tests/ -v --timeout=45 --timeout-method=thread
```

## Next Steps

1. Fix the 5 failing tests
2. Ensure all tests complete within 45 seconds
3. Add more unit tests to increase coverage
4. Set up CI/CD to run tests automatically

