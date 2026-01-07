# LLM Re-extraction Functionality - Code Review

## Overview
The LLM re-extraction functionality is designed to improve low-confidence fields extracted by Document Intelligence (DI) by using Azure OpenAI to re-evaluate and correct them.

## Architecture Flow

### 1. **Trigger Point** (`extract_invoice` method, lines 225-384)

The LLM fallback is triggered automatically during the initial extraction process:

1. **Low-Confidence Field Detection** (lines 227-283):
   - Threshold: 0.75 (hard-coded)
   - Checks three categories:
     - **Required fields**: `invoice_number`, `invoice_date`, `vendor_name`, `total_amount`, `vendor_address`, `bill_to_address`, `remit_to_address`
     - **Blank fields**: Any field that is None, empty string, "Not Extracted", or empty dict/list
     - **Low confidence fields**: Any field with confidence < 0.75 or None

2. **Decision Logic** (lines 285-310):
   - Skips if `DEMO_MODE=True` OR `USE_LLM_FALLBACK=False`
   - Skips if no low-confidence fields found
   - Uses demo LLM if `DEMO_MODE=True` and AOAI not configured
   - Uses real LLM if `USE_LLM_FALLBACK=True` and AOAI configured

3. **Execution** (lines 311-372):
   - Runs in threadpool (synchronous function called asynchronously)
   - Tracks progress via `progress_tracker`
   - Saves only if changes detected (`llm_changed` flag)

### 2. **Real LLM Fallback** (`_run_low_confidence_fallback`, lines 541-734)

#### Field Grouping (lines 573-589)
Fields are processed in groups to reduce payload size:
- **Group 1**: Basic fields (invoice_number, dates, vendor, customer, financial)
- **Group 2**: Addresses (vendor_address, bill_to_address, remit_to_address)
- **Group 3**: Line items (fields starting with "line_items")

#### Caching (lines 615-622)
- Cache key: `(deployment_name, sorted_fields_tuple, file_name, sanitized_di_snapshot)`
- In-memory dictionary cache (lost on service restart)
- Prevents duplicate LLM calls for identical requests

#### LLM API Call (lines 632-705)
- **Client**: AzureOpenAI with endpoint, API key, deployment name
- **Temperature**: 0.0 (deterministic)
- **Retry Logic**:
  - Max 3 retries
  - Exponential backoff (1s → 2s → 4s, max 60s)
  - Special handling for 429 (rate limit) errors
  - Respects `retry_after` header if present

#### Response Processing (lines 711-730)
- Extracts content from `resp.choices[0].message.content`
- Caches response
- Parses JSON using `_coerce_llm_json`
- Applies suggestions using `_apply_llm_suggestions`

### 3. **Mock LLM Fallback** (`_run_mock_llm_fallback`, lines 735-807)

Used in demo mode when AOAI is not configured:
- Uses deterministic heuristics
- Looks for values in canonical data or raw DI data
- Promotes confidence to 0.9 for successfully found fields
- No external API calls

### 4. **Prompt Building** (`_build_llm_prompt`, lines 818-847)

**System Prompt** (lines 65-100):
- Defines LLM role as "specialized invoice extraction QA assistant"
- Lists all canonical field names
- Specifies formatting rules (dates, amounts, addresses)

**User Prompt** (lines 836-847):
- JSON payload with:
  - `low_confidence_fields`: List of field names
  - `fields`: Sanitized field values (only low-confidence ones)
  - `ocr_snippet`: First 1200 chars + last 800 chars of OCR text (if available)

### 5. **Suggestion Application** (`_apply_llm_suggestions`, lines 868-952)

**Validation** (lines 885-894):
- Only accepts canonical field names (from `CANONICAL_FIELDS` set)
- Removes non-canonical fields with warning

**Field Type Handling**:
- **Decimals**: `subtotal`, `tax_amount`, `total_amount`, `acceptance_percentage` → parsed via `_parse_decimal`
- **Dates**: Various date fields → parsed via `dateutil.parser.parse`
- **Addresses**: Dict → converted to `Address` model
- **Others**: Direct assignment

**Confidence Update**:
- Sets field confidence to 0.9 for all LLM-corrected fields
- Recalculates overall extraction confidence

### 6. **JSON Parsing** (`_coerce_llm_json`, lines 1002-1048)

Robust JSON extraction with multiple fallback strategies:
1. Direct JSON parse
2. Extract from code fences (```json ... ```)
3. Extract from first `{` to last `}`
4. Single-quote to double-quote normalization

### 7. **Re-extraction Endpoint** (`/api/hitl/invoice/{invoice_id}/reextract`, lines 1110-1156)

- Resets invoice state via `DatabaseService.reset_for_reextract`
- Calls `extract_invoice` again (full DI + LLM flow)
- Returns updated invoice in HITL format

## Key Issues & Observations

### ✅ **Strengths**
1. **Field Grouping**: Reduces token usage by processing fields in batches
2. **Caching**: Prevents duplicate LLM calls
3. **Retry Logic**: Handles rate limits and transient errors
4. **Validation**: Only accepts canonical field names
5. **Error Handling**: Comprehensive logging and graceful degradation

### ⚠️ **Potential Issues** - **ALL RESOLVED** ✅

1. **Synchronous Execution in Threadpool**: ✅ **RESOLVED**
   - `_run_low_confidence_fallback` is now fully async (converted from sync)
   - Uses `AsyncAzureOpenAI` client with `await` calls
   - No longer blocks threads during LLM calls
   - **Resolution**: Method converted to async, all LLM calls use `await`

2. **In-Memory Cache**: ✅ **RESOLVED**
   - Implemented `TTLCache` class with configurable TTL (default 3600s) and max size (default 1000)
   - Automatic cleanup of expired entries
   - LRU eviction when cache exceeds max size
   - **Resolution**: Cache now has TTL and size limits, preventing memory leaks

3. **Hard-Coded Threshold**: ✅ **RESOLVED**
   - `low_conf_threshold` is now configurable via `settings.LLM_LOW_CONF_THRESHOLD`
   - Defaults to 0.75 if not set
   - **Resolution**: Can be tuned via environment variable without code changes

4. **No Partial Success Handling**: ✅ **RESOLVED**
   - Tracks per-group success/failure independently
   - Returns detailed results dictionary with per-group status
   - Continues processing other groups if one fails
   - Overall success determined if at least one group succeeds
   - **Resolution**: Comprehensive per-group tracking and partial success support

5. **Confidence Always Set to 0.9**: ✅ **RESOLVED**
   - Implemented `_calculate_llm_confidence` method with dynamic confidence scoring
   - Considers context: blank field filled (0.85-0.95), wrong value corrected (0.75-0.85), value confirmed (0.70-0.80)
   - Adjusts based on original confidence and field importance
   - **Resolution**: Confidence now dynamically calculated based on correction context

6. **OCR Snippet Truncation**: ✅ **RESOLVED**
   - Enhanced `_build_content_snippet` to intelligently extract OCR context
   - For multi-page: includes first page, middle page(s), and last page
   - For single-page: includes beginning, middle, and end sections
   - Configurable max chars via `settings.LLM_OCR_SNIPPET_MAX_CHARS`
   - **Resolution**: OCR snippets now include comprehensive document context

7. **No LLM Response Validation**: ✅ **RESOLVED**
   - Implemented `_validate_llm_suggestion` method with comprehensive validation
   - Validates dates (not too far in future, date logic), amounts (not negative, reasonable size), tax rates, percentages, strings, addresses
   - Invalid suggestions are rejected with warning logs
   - **Resolution**: All LLM suggestions validated before application

8. **Re-extraction Clears All Fields**: ⚠️ **VERIFIED - BY DESIGN**
   - `reset_for_reextract` only resets processing state, not field values
   - Fields are cleared during re-extraction as part of the extraction flow
   - **Status**: This is intentional behavior for re-extraction

9. **No Progress Updates During LLM Calls**: ✅ **RESOLVED**
   - Added background progress update task that runs in parallel with LLM calls
   - Sends periodic updates every 7 seconds during long LLM calls
   - Updates progress at key points: before calls, during retries, after group completion
   - **Resolution**: Users now see progress updates throughout LLM processing

10. **Canadian Tax Fields Not in LLM Prompt**: ✅ **RESOLVED**
    - Canadian tax fields are included in the "canadian_taxes" group
    - All 58 canonical fields are now in the LLM system prompt
    - **Resolution**: Tax fields are evaluated by LLM when low confidence

## Recommendations

### ✅ **Completed (High Priority)**
1. ✅ **Make LLM calls truly async**: Converted to fully async with `AsyncAzureOpenAI`
2. ✅ **Add cache TTL/size limits**: Implemented `TTLCache` with TTL and LRU eviction
3. ✅ **Make threshold configurable**: Added `LLM_LOW_CONF_THRESHOLD` setting
4. ✅ **Handle partial success**: Implemented per-group tracking and partial success handling
5. ✅ **Validate LLM responses**: Added comprehensive field validation before applying suggestions
6. ✅ **Add progress updates during LLM calls**: Background task sends periodic updates
7. ✅ **Include tax fields in grouping**: Canadian tax fields included in LLM evaluation

### 🔄 **Future Enhancements (Medium Priority)**
8. **Preserve manual corrections on re-extract**: Only reset auto-extracted fields
9. **Add LLM confidence scores**: If LLM provides confidence, use it instead of calculated confidence
10. **Add metrics**: Track LLM call count, success rate, average latency, cache hit rate
11. **Add circuit breaker**: Stop calling LLM if error rate too high

### 📋 **Future Enhancements (Low Priority)**
12. **Persistent cache**: Use Redis or similar for cache across restarts
13. **Streaming responses**: Stream LLM responses for faster perceived performance
14. **Field-specific prompts**: Optimize prompts per field group for better accuracy

## Code Quality

- **Error Handling**: ✅ Comprehensive
- **Logging**: ✅ Good coverage
- **Type Hints**: ⚠️ Some missing (e.g., `_sanitize_for_json` return type)
- **Documentation**: ✅ Good docstrings
- **Testing**: ❓ Need to check test coverage

## Performance Considerations

- **Token Usage**: Field grouping helps reduce payload size
- **Latency**: 3 groups × 10-30s each = 30-90s total LLM time (now with progress updates)
- **Concurrency**: Fully async implementation allows better concurrency
- **Cache Hit Rate**: TTL cache with LRU eviction prevents memory issues
- **Progress Updates**: Users see periodic updates every 7 seconds during long calls

## Recent Improvements (All Issues Resolved)

### ✅ **Issue #1: Async Execution**
- Converted `_run_low_confidence_fallback` to fully async
- Uses `AsyncAzureOpenAI` client
- No thread blocking during LLM calls

### ✅ **Issue #2: Cache Management**
- Implemented `TTLCache` class with TTL (3600s) and max size (1000)
- Automatic cleanup of expired entries
- LRU eviction when cache is full

### ✅ **Issue #3: Configurable Threshold**
- Added `LLM_LOW_CONF_THRESHOLD` setting (default: 0.75)
- Configurable via environment variable

### ✅ **Issue #4: Partial Success Handling**
- Per-group success/failure tracking
- Detailed results dictionary
- Continues processing even if some groups fail

### ✅ **Issue #5: Dynamic Confidence Scoring**
- `_calculate_llm_confidence` method considers context
- Different confidence ranges for blank fills, corrections, confirmations
- Adjusts based on original confidence and field importance

### ✅ **Issue #6: Enhanced OCR Snippets**
- Intelligent extraction from first, middle, and last sections
- Multi-page document support
- Configurable max characters via `LLM_OCR_SNIPPET_MAX_CHARS`

### ✅ **Issue #7: LLM Response Validation**
- `_validate_llm_suggestion` validates dates, amounts, rates, strings, addresses
- Rejects invalid suggestions with detailed error messages
- Prevents incorrect data from being applied

### ✅ **Issue #9: Progress Updates**
- Background task sends periodic updates every 7 seconds
- Updates at key points: before calls, during retries, after completion
- Users see progress throughout long LLM processing

