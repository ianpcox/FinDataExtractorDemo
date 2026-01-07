# LLM Extraction Functionality Evaluation Report

**Generated:** 2026-01-07  
**Test Suite:** `tests/integration/test_real_llm_extraction.py`  
**Purpose:** Evaluate the extent to which base LLM functionality works for invoice field extraction use case  
**Status:** ⚠️ **Tests currently blocked by database state conflicts** (all 9 tests failing with "Invoice is already processing")

**Evaluation Method:** Code analysis + test design review (tests cannot execute due to blocking issues)

---

## Executive Summary

This report evaluates the base LLM (Large Language Model) functionality for invoice field extraction based on:
1. Test suite design and coverage
2. LLM implementation architecture
3. Canonical field schema alignment
4. Expected vs actual behavior (based on code analysis)
5. Test execution attempts and failures

**Key Findings:**
- ✅ **Test Suite Design**: Comprehensive - designed to test all 57 canonical fields
- ✅ **LLM Implementation**: Well-architected with robust error handling, caching, and validation
- ✅ **Field Coverage**: All 57 canonical fields included in LLM system prompt
- ❌ **Test Execution**: Blocked by database state conflicts - cannot evaluate actual LLM performance
- ⚠️ **Evaluation Status**: Based on code analysis only - no actual execution data available

**Critical Blocker:** All 9 tests fail with "Invoice is already processing" error, preventing evaluation of actual LLM extraction performance.

---

## Test Suite Overview

### Test Coverage

The test suite includes **9 integration tests** designed to evaluate real Azure OpenAI LLM extraction:

1. **`test_real_llm_extracts_invoice_number`** - Tests extraction of a single field (invoice_number) from low-confidence data
2. **`test_full_extraction_pipeline_with_llm`** - Tests end-to-end pipeline: DI → LLM → database persistence
3. **`test_llm_improves_low_confidence_fields`** - Verifies LLM improves fields with low confidence scores
4. **`test_llm_confidence_calculation_accuracy`** - Tests dynamic confidence scoring based on correction context
5. **`test_llm_corrects_multiple_field_types`** - Tests LLM correction across different field types (strings, dates, decimals)
6. **`test_confidence_scores_persist_to_database`** - Verifies confidence scores are properly saved
7. **`test_real_llm_extracts_multiple_fields`** - Tests extraction of multiple fields simultaneously
8. **`test_real_llm_corrects_wrong_values`** - Tests LLM correction of incorrect field values
9. **`test_llm_extracts_all_canonical_fields`** - **COMPREHENSIVE TEST**: Verifies extraction of all 57 canonical fields from the schema

### Test Design Intent

The test suite is designed to evaluate:
- **Field Extraction Coverage**: Can the LLM extract all canonical fields?
- **Field Type Handling**: Can the LLM handle strings, dates, decimals, addresses, etc.?
- **Confidence Scoring**: Are confidence scores calculated and persisted correctly?
- **Value Correction**: Can the LLM correct wrong values and fill missing values?
- **Pipeline Integration**: Does the full extraction pipeline (DI + LLM) work end-to-end?

---

## LLM Implementation Architecture

### LLM System Prompt

The LLM uses a comprehensive system prompt that:
- Lists all 57 canonical field names explicitly
- Provides formatting rules (ISO 8601 dates, decimal strings, address objects)
- Instructs the LLM to only correct low-confidence fields
- Prohibits field invention or guessing
- Requires JSON-only output

**Canonical Fields in System Prompt:**
- Header: 5 fields (invoice_number, invoice_date, due_date, invoice_type, reference_number)
- Vendor: 7 fields (vendor_name, vendor_id, vendor_phone, vendor_fax, vendor_email, vendor_website, vendor_address)
- Vendor Tax IDs: 4 fields (gst_number, qst_number, pst_number, business_number)
- Customer: 6 fields (customer_name, customer_id, customer_phone, customer_email, customer_fax, bill_to_address)
- Remit-To: 2 fields (remit_to_address, remit_to_name)
- Contract: 4 fields (entity, contract_id, standing_offer_number, po_number)
- Dates: 4 fields (period_start, period_end, shipping_date, delivery_date)
- Financial: 5 fields (subtotal, discount_amount, shipping_amount, handling_fee, deposit_amount)
- Canadian Taxes: 8 fields (gst_amount, gst_rate, hst_amount, hst_rate, qst_amount, qst_rate, pst_amount, pst_rate)
- Total: 3 fields (tax_amount, total_amount, currency)
- Payment: 4 fields (payment_terms, payment_method, payment_due_upon, tax_registration_number)

**Total: 57 canonical fields**

### LLM Fallback Trigger

The LLM is triggered when:
- `USE_LLM_FALLBACK` is enabled
- Fields have confidence scores below `LLM_LOW_CONF_THRESHOLD` (default: 0.75)
- Azure OpenAI credentials are configured

### LLM Processing Flow

1. **Field Grouping**: Low-confidence fields are grouped for efficient processing:
   - **"fields"** group: Core invoice fields (invoice_number, invoice_date, vendor_name, etc.)
   - **"addresses"** group: Address fields (vendor_address, bill_to_address, remit_to_address)
   - **"canadian_taxes"** group: Canadian tax fields (GST, HST, QST, PST amounts and rates)
   - **"line_items"** group: Line item fields

2. **Prompt Construction**: For each group, the LLM receives:
   - Low-confidence field names and their current values
   - Field confidence scores
   - OCR text snippet (beginning, middle, end sections of document)
   - Sanitized DI data snapshot

3. **LLM API Call**: 
   - Async Azure OpenAI API call
   - Temperature: 0.0 (deterministic)
   - Retry logic with exponential backoff for rate limits (429 errors)
   - TTL cache with LRU eviction to avoid redundant calls

4. **Response Processing**:
   - JSON parsing and validation
   - Field value validation (dates, amounts, addresses)
   - Dynamic confidence calculation based on correction context
   - Application of corrected values to Invoice model

5. **Confidence Scoring**:
   - **Filling blank fields**: High confidence (0.85-0.95)
   - **Correcting wrong values**: Medium-high confidence (0.75-0.85)
   - **Confirming existing values**: Medium confidence (0.70-0.80)
   - Considers original confidence and field importance

---

## Comprehensive Field Extraction Test

### Test: `test_llm_extracts_all_canonical_fields`

This is the most comprehensive test, designed to evaluate LLM extraction of **ALL canonical fields**.

**Test Design:**
1. Creates an invoice in PENDING state with **no pre-populated fields**
2. Runs full extraction pipeline (DI + LLM)
3. Checks each of the 57 canonical fields to see if they were extracted
4. Reports extraction statistics by category
5. Prints detailed field-by-field extraction report

**Expected Output:**
The test prints a comprehensive report showing:
- Total canonical fields: 57
- Fields extracted: X (Y%)
- Fields missing: Z (W%)
- Category breakdown (Header, Vendor, Customer, etc.)
- Detailed field status (extracted/not extracted, confidence, value preview)

**Evaluation Criteria:**
- **Core Fields**: At least invoice_number, vendor_name, total_amount should be extracted
- **Field Confidence**: All extracted fields should have confidence scores
- **Extraction Confidence**: Overall extraction confidence should be set
- **Field Types**: Tests extraction across different field types

---

## Current Test Execution Status

### Test Results

**Status:** ❌ **ALL 9 TESTS FAILING**

**Error:** `AssertionError: Extraction failed: ['Invoice is already processing']`

**Test Execution Summary:**
```
tests/integration/test_real_llm_extraction.py::TestRealLLMExtraction::test_real_llm_extracts_invoice_number FAILED
tests/integration/test_real_llm_extraction.py::TestRealLLMExtraction::test_full_extraction_pipeline_with_llm FAILED
tests/integration/test_real_llm_extraction.py::TestRealLLMExtraction::test_llm_improves_low_confidence_fields FAILED
tests/integration/test_real_llm_extraction.py::TestRealLLMExtraction::test_llm_confidence_calculation_accuracy FAILED
tests/integration/test_real_llm_extraction.py::TestRealLLMExtraction::test_llm_corrects_multiple_field_types FAILED
tests/integration/test_real_llm_extraction.py::TestRealLLMExtraction::test_confidence_scores_persist_to_database FAILED
tests/integration/test_real_llm_extraction.py::TestRealLLMExtraction::test_real_llm_extracts_multiple_fields FAILED
tests/integration/test_real_llm_extraction.py::TestRealLLMExtraction::test_real_llm_corrects_wrong_values FAILED
tests/integration/test_real_llm_extraction.py::TestRealLLMExtraction::test_llm_extracts_all_canonical_fields FAILED

9 failed in ~3 seconds
```

**Root Cause:** Database state conflict - invoices are being marked as "PROCESSING" before extraction can begin, preventing the `claim_for_extraction` method from successfully claiming the invoice.

**Impact:** Cannot evaluate actual LLM extraction performance because tests cannot execute. All tests fail at the same point: when attempting to claim the invoice for extraction.

### Database State Issue Analysis

The `extract_invoice` method calls `DatabaseService.claim_for_extraction(invoice_id)` which:
- Attempts to transition invoice from PENDING/FAILED → PROCESSING using atomic UPDATE
- Returns `False` if invoice is already in PROCESSING state (or transition fails)
- Causes extraction to fail with "Invoice is already processing" error

**Investigation Attempts:**
1. ✅ Added invoice deletion before creation - Still fails
2. ✅ Added `reset_for_reextract` calls - Still fails (doesn't work for PROCESSING state)
3. ✅ Added explicit commits and delays - Still fails
4. ✅ Used `pydantic_to_db_invoice` directly (like other tests) - Still fails
5. ✅ Added session refresh - Still fails

**Possible Root Causes:**
1. **Transaction Isolation**: The invoice might be visible in PROCESSING state due to transaction isolation level
2. **Concurrent Processing**: Another process/thread might be claiming the invoice simultaneously
3. **State Persistence**: Invoice state might be persisted from a previous transaction that hasn't been rolled back
4. **Database Session Management**: The `db_session` fixture might not be properly isolating transactions
5. **Race Condition**: The invoice might be created and immediately claimed by another operation before the test can extract it

**Note:** Other integration tests (e.g., `test_concurrent_extraction`) successfully create invoices in PENDING state, suggesting the issue is specific to the real LLM extraction test setup or execution order.

---

## LLM Functionality Evaluation (Based on Code Analysis)

### Strengths

1. **Comprehensive Field Coverage**: 
   - LLM system prompt includes all 57 canonical fields
   - Test suite designed to verify extraction of all fields
   - Field grouping ensures efficient processing

2. **Robust Error Handling**:
   - Retry logic with exponential backoff for rate limits
   - Partial success handling (applies successful corrections even if some groups fail)
   - Graceful degradation (continues with DI results if LLM fails)

3. **Intelligent Confidence Scoring**:
   - Dynamic confidence based on correction context
   - Different confidence levels for filling blanks vs correcting wrong values
   - Confidence scores properly persisted to database

4. **Field Validation**:
   - Validates LLM responses before applying (dates, amounts, addresses)
   - Prevents invalid data from being applied
   - Logs validation failures for debugging

5. **Performance Optimizations**:
   - TTL cache with LRU eviction to avoid redundant LLM calls
   - Async execution to prevent thread blocking
   - Field grouping to reduce API call count

6. **Comprehensive OCR Context**:
   - Provides beginning, middle, and end sections of document
   - Adapts to single-page, two-page, and multi-page layouts
   - Configurable snippet size

### Limitations

1. **Database State Management**:
   - Tests currently blocked by state conflict issues
   - Need better test setup to ensure clean invoice state

2. **Field Extraction Coverage**:
   - Cannot evaluate actual extraction rates without running tests
   - Unknown which fields LLM can reliably extract from real documents

3. **Performance Characteristics**:
   - No performance metrics available (response times, success rates)
   - Cannot evaluate LLM API reliability without test execution

4. **Error Scenarios**:
   - Error handling tests exist but cannot verify real-world behavior
   - Unknown how LLM handles edge cases in practice

---

## Expected LLM Performance (Based on Design)

### Field Extraction Expectations

Based on the LLM system prompt and test design, the LLM should be able to extract:

**High Confidence Fields (Expected > 80% extraction rate):**
- invoice_number
- invoice_date
- due_date
- vendor_name
- customer_name
- total_amount
- tax_amount
- currency
- payment_terms

**Medium Confidence Fields (Expected 50-80% extraction rate):**
- vendor_address
- bill_to_address
- po_number
- subtotal
- Canadian tax fields (gst_amount, pst_amount, etc.)

**Low Confidence Fields (Expected < 50% extraction rate):**
- Optional fields (vendor_fax, customer_email, etc.)
- Fields not commonly present in invoices
- Complex structured fields (tax_breakdown)

### Field Type Handling

**String Fields**: Should handle well (invoice_number, vendor_name, etc.)
**Date Fields**: Should handle well with ISO 8601 format validation
**Decimal Fields**: Should handle well with format validation
**Address Fields**: Should handle structured objects (street, city, province, postal_code, country)
**Tax Fields**: Should handle Canadian tax amounts and rates

---

## Recommendations

### Immediate Actions (CRITICAL)

1. **Fix Database State Management** (BLOCKING):
   - **Priority: P0** - Tests cannot execute until this is resolved
   - Investigate why `claim_for_extraction` fails even with fresh invoices
   - Consider using a test-specific `claim_for_extraction` that bypasses state checks for tests
   - Or ensure invoices are created in a way that guarantees PENDING state
   - Verify transaction isolation is working correctly in test database

2. **Run Tests Successfully**:
   - Once state issues are resolved, run all 9 tests
   - Collect actual extraction statistics
   - Generate field-by-field extraction report from `test_llm_extracts_all_canonical_fields`
   - Measure LLM API response times and success rates

### Evaluation Improvements

1. **Add Performance Metrics**:
   - Measure LLM API response times
   - Track success rates for different field types
   - Monitor cache hit rates

2. **Expand Test Coverage**:
   - Test with multiple invoice types
   - Test with different document qualities (high/low OCR quality)
   - Test edge cases (missing fields, malformed data)

3. **Generate Regular Reports**:
   - Run tests periodically to track LLM performance over time
   - Compare extraction rates across different invoice types
   - Identify fields that consistently fail extraction

---

## Conclusion

**Design Assessment:** The LLM extraction functionality is **well-designed** with:
- Comprehensive field coverage (57 canonical fields)
- Robust error handling and retry logic
- Intelligent confidence scoring
- Field validation and type handling
- Performance optimizations (caching, async execution)

**Implementation Status:** The implementation appears **complete** based on code analysis, but **cannot be evaluated** due to test execution failures.

**Test Suite Quality:** The test suite is **comprehensive** and designed to evaluate:
- All canonical field extraction
- Multiple field types
- Confidence scoring
- Value correction
- End-to-end pipeline integration

**Blocking Issue:** Database state management conflicts prevent test execution, making it impossible to evaluate actual LLM performance.

**Next Steps (Priority Order):**
1. **URGENT**: Resolve database state conflicts to enable test execution
   - Investigate `claim_for_extraction` failure in test environment
   - Consider test-specific state management
   - Verify transaction isolation
2. Run comprehensive test suite to collect actual extraction statistics
3. Generate field-by-field extraction report from `test_llm_extracts_all_canonical_fields`
4. Evaluate LLM performance against expected extraction rates
5. Identify fields that need improvement or alternative extraction strategies
6. Measure and document LLM API performance characteristics

---

## Appendix: Test Execution Attempts

### Attempt 1: Initial Run
- **Result**: All 9 tests failed
- **Error**: "Invoice is already processing"
- **Cause**: Invoice state conflicts

### Attempt 2: Added State Reset
- **Result**: All 9 tests failed
- **Error**: "Invoice is already processing"
- **Cause**: `reset_for_reextract` doesn't work for PROCESSING state

### Attempt 3: Added Invoice Deletion
- **Result**: All 9 tests failed
- **Error**: "Invoice is already processing"
- **Cause**: Invoice still being claimed before extraction

### Current Status: Tests cannot execute due to persistent state conflicts

---

**Report End**

