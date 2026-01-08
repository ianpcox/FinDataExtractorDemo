# Real PDF Integration Tests

## Overview

The `test_real_pdf_integration.py` test suite provides comprehensive integration tests using actual PDF files from the sample invoices directory. These tests validate the complete extraction pipeline including line items and aggregation validation.

## Test Suite

### Location
`tests/integration/test_real_pdf_integration.py`

### Test Class
`TestRealPDFIntegration`

## Test Cases

### 1. `test_real_pdf_extraction_with_line_items`
**Purpose**: Test full extraction pipeline with real PDFs including line item extraction.

**What it tests**:
- Full extraction pipeline with real Azure Document Intelligence API calls
- Line item extraction from actual invoices
- Line item structure validation (line_number, description, amount)
- Basic field extraction (invoice_number, vendor_name)

**Assertions**:
- Extraction succeeds
- Invoice is saved to database
- At least basic fields are extracted
- Line items have valid structure if present

**Output**: Prints number of line items extracted per PDF

### 2. `test_real_pdf_aggregation_validation`
**Purpose**: Test aggregation validation with real PDF extraction.

**What it tests**:
- Aggregation validation runs automatically during extraction
- Validation results are included in extraction response
- Validation summary structure is correct
- Validation handles cases with and without line items

**Assertions**:
- Aggregation validation is present in result when line items exist
- Validation summary contains expected fields
- Validation results are logged appropriately

**Output**: Prints aggregation validation results for each PDF

### 3. `test_real_pdf_line_item_field_extraction`
**Purpose**: Test that individual line item fields are correctly extracted.

**What it tests**:
- Line item field extraction (description, quantity, unit_price, amount)
- Tax field extraction (tax_amount, gst_amount, pst_amount, qst_amount)
- Field validation (quantity * unit_price = amount)
- Field completeness

**Assertions**:
- Line item description is extracted
- Line item amount is extracted
- Amount matches quantity * unit_price (if both present)
- Tax fields are extracted when available

**Output**: Prints detailed line item field information for first 5 items

### 4. `test_real_pdf_end_to_end_with_validation`
**Purpose**: Test complete end-to-end extraction with all validations.

**What it tests**:
- Complete extraction workflow
- Result structure completeness
- Business rule validation
- Aggregation validation integration
- Database persistence

**Assertions**:
- Result contains all expected fields
- Invoice is saved correctly
- Validation results are present
- Aggregation validation is included when line items exist

**Output**: Prints comprehensive extraction summary

### 5. `test_real_pdf_specific_invoice`
**Purpose**: Test extraction of a specific known invoice PDF with detailed validation.

**What it tests**:
- Extraction of a specific PDF (ACC012 4202092525.pdf)
- Detailed field extraction validation
- Line item extraction and structure
- Aggregation validation results
- Complete invoice data integrity

**Assertions**:
- Key fields are extracted
- Line items are structured correctly
- Aggregation validation runs
- All data is consistent

**Output**: Prints detailed extraction results and validation summary

## Requirements

### Azure Document Intelligence
- `AZURE_FORM_RECOGNIZER_ENDPOINT` must be configured
- `AZURE_FORM_RECOGNIZER_KEY` must be configured
- Tests will be skipped if credentials are not available

### Sample PDFs
- PDF files must exist in `data/sample_invoices/Raw/Raw_Basic/`
- Tests use first 3 PDFs found in the directory
- Specific test uses `ACC012 4202092525.pdf`

### Database
- Each test uses an isolated test database
- Database is automatically created and cleaned up
- No shared state between tests

## Running the Tests

### Run all real PDF integration tests:
```bash
pytest tests/integration/test_real_pdf_integration.py -v
```

### Run a specific test:
```bash
pytest tests/integration/test_real_pdf_integration.py::TestRealPDFIntegration::test_real_pdf_extraction_with_line_items -v
```

### Run with markers:
```bash
# Run only integration tests
pytest -m integration tests/integration/test_real_pdf_integration.py

# Run only slow tests (includes these)
pytest -m slow tests/integration/test_real_pdf_integration.py
```

### Skip if credentials not available:
Tests automatically skip if Azure credentials are not configured:
```bash
pytest tests/integration/test_real_pdf_integration.py -v -s
```

## Test Behavior

### LLM Fallback
- LLM fallback is **disabled** during these tests
- Tests focus on Document Intelligence extraction only
- Original LLM setting is restored after each test

### Test Isolation
- Each test uses a unique invoice ID (UUID-based)
- Each test uses an isolated database session
- No test pollution or shared state

### Error Handling
- Tests skip gracefully if PDFs are not found
- Tests skip gracefully if file upload fails
- Tests skip gracefully if Azure credentials are missing
- Detailed error messages for debugging

## Expected Output

### Successful Test Run
```
tests/integration/test_real_pdf_integration.py::TestRealPDFIntegration::test_real_pdf_extraction_with_line_items PASSED

✓ ACC012 4202092525.pdf: Extracted 5 line items
✓ ANA005 90443097.pdf: Extracted 3 line items
✓ ENB001 166574659065NOV2025.pdf: No line items extracted (may be normal for some invoices)
```

### Aggregation Validation Output
```
ACC012 4202092525.pdf - Aggregation Validation:
  All Valid: True
  Passed: 6/6
  ✓ All aggregations valid
```

### Line Item Field Output
```
ACC012 4202092525.pdf - Line Item Fields:
  Line 1:
    Description: Professional Services...
    Amount: 1500.00
    Quantity: 10
    Unit Price: 150.00
    ✓ Amount matches quantity * unit_price
```

## Integration with Other Tests

### Related Test Suites
- `test_real_di_extraction.py`: Tests DI field extraction (no line items focus)
- `test_line_item_extraction_and_aggregation.py`: Tests line items with mocks
- `test_end_to_end.py`: Tests end-to-end workflow with mocks

### Complementary Coverage
- **Unit tests**: Test individual components with mocks
- **Mock integration tests**: Test integration logic without external calls
- **Real PDF integration tests**: Test complete pipeline with real PDFs and APIs

## Benefits

1. **Real-world validation**: Tests actual PDF extraction, not just mocks
2. **Line item focus**: Specifically validates line item extraction and aggregation
3. **Comprehensive**: Tests full pipeline from PDF to database
4. **Isolated**: Each test is independent with no shared state
5. **Informative**: Detailed output for debugging and validation
6. **Robust**: Graceful handling of missing resources

## Future Enhancements

1. **Ground truth comparison**: Compare extracted values against known ground truth
2. **Performance metrics**: Track extraction time and API call counts
3. **Coverage tracking**: Track which fields are extracted from which PDFs
4. **Regression detection**: Compare extraction results across test runs
5. **Multi-PDF batch testing**: Test extraction of multiple PDFs in parallel
6. **Error scenario testing**: Test handling of corrupted or invalid PDFs
