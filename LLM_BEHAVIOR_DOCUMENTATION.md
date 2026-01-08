# LLM Behavior Documentation

**Last Updated:** 2026-01-07  
**Version:** 1.0

---

## Table of Contents

1. [Overview](#overview)
2. [When LLM Fallback is Triggered](#when-llm-fallback-is-triggered)
3. [Confidence Score Updates](#confidence-score-updates)
4. [Field Formatting Rules](#field-formatting-rules)
5. [LLM Prompt Best Practices](#llm-prompt-best-practices)
6. [Configuration Settings](#configuration-settings)
7. [Error Handling](#error-handling)
8. [Multimodal LLM Fallback](#multimodal-llm-fallback)

---

## Overview

The LLM (Large Language Model) fallback system is a quality assurance mechanism that improves invoice extraction accuracy by re-evaluating low-confidence fields extracted by Azure Document Intelligence (DI). The system uses Azure OpenAI GPT-4o to analyze low-confidence fields and provide corrected values based on the original OCR text and extracted data.

### Key Features

- **Automatic Triggering**: LLM fallback is automatically triggered for fields with confidence below a configurable threshold
- **Dynamic Confidence Scoring**: Confidence scores are dynamically calculated based on the context of LLM corrections
- **Field Validation**: All LLM suggestions are validated before being applied to prevent invalid data
- **Caching**: LLM responses are cached to reduce API calls and costs
- **Partial Success Handling**: The system continues processing even if some field groups fail
- **Multimodal Support**: Supports both text-based and image-based (multimodal) LLM fallback for scanned PDFs

---

## When LLM Fallback is Triggered

### Primary Trigger Conditions

LLM fallback is triggered when **all** of the following conditions are met:

1. **LLM Fallback is Enabled**: `USE_LLM_FALLBACK` setting must be `True`
2. **Azure OpenAI is Configured**: Valid credentials must be present:
   - `AOAI_ENDPOINT`
   - `AOAI_API_KEY`
   - `AOAI_DEPLOYMENT_NAME`
3. **Low-Confidence Fields Exist**: At least one field has confidence below `LLM_LOW_CONF_THRESHOLD` (default: 0.75)
4. **Document Intelligence Extraction Completed**: DI extraction must have completed successfully

### Confidence Threshold

The confidence threshold is configurable via the `LLM_LOW_CONF_THRESHOLD` environment variable:

```python
LLM_LOW_CONF_THRESHOLD: float = 0.75  # Default: 0.75 (75%)
```

**Fields with confidence < threshold are sent to LLM for re-evaluation.**

### Field Selection Logic

The system identifies low-confidence fields using the following logic:

```python
low_conf_fields = []
for field_name, confidence in field_confidence.items():
    if confidence is not None and confidence < LLM_LOW_CONF_THRESHOLD:
        low_conf_fields.append(field_name)
```

Additionally, required fields with missing values or no confidence are automatically included:

- `invoice_number`
- `invoice_date`
- `vendor_name`
- `total_amount`
- `vendor_address`
- `bill_to_address`
- `remit_to_address`

### Field Grouping

Fields are grouped into logical categories to reduce API payload size and improve processing efficiency:

1. **Fields Group**: Core invoice fields (invoice_number, invoice_date, vendor_name, etc.)
2. **Addresses Group**: Address fields (vendor_address, bill_to_address, remit_to_address)
3. **Line Items Group**: Line item fields (line_items.*)

Each group is processed separately, allowing partial success if one group fails.

### When LLM Fallback is NOT Triggered

LLM fallback is **skipped** in the following scenarios:

1. **LLM Disabled**: `USE_LLM_FALLBACK=False`
2. **No Low-Confidence Fields**: All fields have confidence >= `LLM_LOW_CONF_THRESHOLD`
3. **Azure OpenAI Not Configured**: Missing required credentials
4. **DI Extraction Failed**: Document Intelligence extraction did not complete successfully

### Manual Triggering

LLM fallback can also be manually triggered via the `run_ai_extraction()` method:

```python
result = await extraction_service.run_ai_extraction(
    invoice_id="invoice-123",
    confidence_threshold=0.7,  # Custom threshold
    db=db_session
)
```

---

## Confidence Score Updates

### Dynamic Confidence Calculation

Confidence scores for LLM-corrected fields are **dynamically calculated** based on the context of the correction, not hard-coded. The `_calculate_llm_confidence()` method considers multiple factors:

#### Base Confidence Ranges

| Scenario | Base Confidence | Rationale |
|----------|----------------|-----------|
| **LLM filled blank field** | 0.90 | High confidence - LLM extracted missing data |
| **LLM corrected wrong value** | 0.80 | Medium-high confidence - LLM fixed existing data |
| **LLM confirmed existing value** | 0.75 | Medium confidence - LLM validated existing value |
| **LLM set to null/blank** | 0.70 | Lower confidence - LLM intentionally cleared field |

#### Original Confidence Adjustments

The system adjusts base confidence based on the original confidence score:

- **Original confidence < 0.5**: +0.05 boost (LLM improvement is more significant)
- **Original confidence > 0.85**: -0.05 reduction (LLM confirmation is less significant)

#### Critical Field Boost

Critical fields receive an additional confidence boost when filled from blank:

- **Critical Fields**: `invoice_number`, `invoice_date`, `total_amount`, `vendor_name`
- **Boost**: +0.03 (capped at 0.95)

### Confidence Score Examples

#### Example 1: LLM Fills Missing Invoice Number

```python
Original:
  invoice_number: None
  confidence: None

LLM Suggestion:
  invoice_number: "4202092525"

Result:
  invoice_number: "4202092525"
  confidence: 0.93  # 0.90 (filled blank) + 0.03 (critical field)
```

#### Example 2: LLM Corrects Wrong Date

```python
Original:
  invoice_date: "2025-12-31"  # Wrong (future date)
  confidence: 0.60

LLM Suggestion:
  invoice_date: "2024-09-25"

Result:
  invoice_date: "2024-09-25"
  confidence: 0.85  # 0.80 (corrected wrong) + 0.05 (original was low)
```

#### Example 3: LLM Confirms Existing Value

```python
Original:
  vendor_name: "ACCURATE fire & safety ltd."
  confidence: 0.72

LLM Suggestion:
  vendor_name: "ACCURATE fire & safety ltd."  # Same value

Result:
  vendor_name: "ACCURATE fire & safety ltd."
  confidence: 0.70  # 0.75 (confirmed) - 0.05 (original was high)
```

### Confidence Score Validation

Confidence scores are always validated to ensure they are within the valid range:

```python
return max(0.0, min(1.0, base_confidence))
```

### Overall Extraction Confidence

After applying LLM suggestions, the overall extraction confidence is recalculated:

```python
invoice.extraction_confidence = field_extractor._calculate_overall_confidence(
    invoice.field_confidence
)
```

This provides a single confidence metric for the entire invoice extraction.

---

## Field Formatting Rules

### Date Fields

**Format**: ISO 8601 date strings (`YYYY-MM-DD`)

**Examples**:
- `"2024-09-25"` ✓
- `"2024-09-25T00:00:00"` ✓ (parsed to date)
- `"09/25/2024"` ✓ (parsed to date)
- `"September 25, 2024"` ✓ (parsed to date)

**Validation Rules**:
- Dates cannot be more than 1 year in the future
- `due_date` must be >= `invoice_date`
- `period_end` must be >= `period_start`
- `delivery_date` must be >= `shipping_date`

**Fields**: `invoice_date`, `due_date`, `period_start`, `period_end`, `shipping_date`, `delivery_date`

### Amount Fields

**Format**: Numeric strings with "." as decimal separator

**Examples**:
- `"1234.56"` ✓
- `"1234"` ✓ (parsed as 1234.00)
- `"$1,234.56"` ✓ (parsed as 1234.56)
- `"-500.00"` ✓ (only for credit notes)

**Validation Rules**:
- Negative amounts only allowed for credit notes
- Maximum reasonable amount: 999,999,999.99
- Must be parseable as Decimal

**Fields**: `subtotal`, `tax_amount`, `total_amount`, `discount_amount`, `shipping_amount`, `handling_fee`, `deposit_amount`, `gst_amount`, `hst_amount`, `qst_amount`, `pst_amount`

### Tax Rate Fields

**Format**: Decimal values between 0.0 and 1.0 (or 0-100%)

**Examples**:
- `"0.05"` ✓ (5%)
- `"0.13"` ✓ (13% HST)
- `"5"` ✓ (parsed as 0.05 if < 1.0, otherwise 0.05)
- `"15"` ✓ (parsed as 0.15 if > 1.0)

**Validation Rules**:
- Must be between 0.0 and 1.0 (or 0-100%)
- Cannot be negative

**Fields**: `gst_rate`, `hst_rate`, `qst_rate`, `pst_rate`

### Address Fields

**Format**: JSON object with structured address components

**Structure**:
```json
{
  "street": "123 Main Street",
  "city": "Ottawa",
  "province": "ON",
  "postal_code": "K1A 0B1",
  "country": "Canada"
}
```

**Validation Rules**:
- All subfields are optional (can be null or empty)
- Postal code format is validated (Canadian format: `A1A 1A1`)
- Country should be a valid country name

**Fields**: `vendor_address`, `bill_to_address`, `remit_to_address`

### String Fields

**Format**: Plain text strings

**Validation Rules**:
- Maximum length: 500 characters (configurable)
- Excessive repetition (>10 consecutive identical characters) is rejected
- Whitespace is trimmed

**Fields**: `invoice_number`, `vendor_name`, `customer_name`, `po_number`, `payment_terms`, etc.

### Currency Field

**Format**: ISO 4217 currency code (3-letter uppercase)

**Examples**:
- `"CAD"` ✓
- `"USD"` ✓
- `"EUR"` ✓

**Fields**: `currency`

### Null Values

LLM can explicitly set fields to `null` to indicate that a field should not be extracted:

```json
{
  "invoice_number": null
}
```

This is useful when the LLM determines that a field is not present in the document.

---

## LLM Prompt Best Practices

### System Prompt Structure

The LLM system prompt (`LLM_SYSTEM_PROMPT`) is designed to:

1. **Define the Role**: "You are a specialized invoice extraction QA assistant for CATSA."
2. **Specify Input Format**: Describe the JSON structure of inputs
3. **Define Task**: Clearly state what the LLM should do
4. **List Canonical Fields**: Provide complete list of all 57 canonical fields
5. **Specify Formatting Rules**: Define exact formatting requirements

### Key Prompt Design Principles

#### 1. Explicit Field Names

**Best Practice**: Always list all canonical field names explicitly in the prompt.

```python
CANONICAL FIELD NAMES (use these EXACTLY):
Header: invoice_number, invoice_date, due_date, invoice_type, reference_number
Vendor: vendor_name, vendor_id, vendor_phone, vendor_fax, vendor_email, vendor_website, vendor_address
...
```

**Why**: Prevents the LLM from inventing field names or using variations.

#### 2. Clear Formatting Rules

**Best Practice**: Provide specific, unambiguous formatting rules.

```python
Formatting rules:
- Dates must be ISO 8601 date strings: "YYYY-MM-DD".
- Monetary amounts must be numeric strings, using "." as the decimal separator (e.g., "1234.56").
- For address fields, return an object with keys: street, city, province, postal_code, country.
```

**Why**: Ensures consistent output format that can be easily parsed and validated.

#### 3. Explicit Constraints

**Best Practice**: Clearly state what the LLM should NOT do.

```python
3. NEVER invent fields, change field names, or guess values that are not strongly supported by the data.
4. If you cannot reliably correct a field, set it to null.
5. Output ONLY a single JSON object whose keys are exactly the field names from `low_conf_fields`.
6. Do NOT include explanations, comments, or extra properties.
```

**Why**: Prevents the LLM from adding extra fields or explanations that would break JSON parsing.

#### 4. Context Provision

**Best Practice**: Provide relevant context (OCR snippet) to help the LLM make informed decisions.

```python
- Optionally, a short OCR text snippet from the invoice PDF.
```

**Why**: OCR context helps the LLM verify and correct field values.

### User Prompt Construction

The user prompt is built dynamically and includes:

1. **Low-Confidence Fields**: List of fields to evaluate
2. **Field Values**: Current values from DI extraction
3. **Field Confidence Scores**: Confidence scores for each field
4. **OCR Snippet**: Relevant text from the document (beginning, middle, end)

**Example User Prompt**:
```json
{
  "low_confidence_fields": ["invoice_number", "invoice_date"],
  "fields": {
    "invoice_number": "4202092525",
    "invoice_date": "2025-09-25"
  },
  "field_confidence": {
    "invoice_number": 0.65,
    "invoice_date": 0.70
  },
  "ocr_snippet": "INVOICE\nInvoice #: 4202092525\nDate: September 25, 2024\n..."
}
```

### OCR Snippet Strategy

The OCR snippet is intelligently constructed to provide maximum context:

- **Single-Page Documents**: Beginning, middle, and end sections
- **Multi-Page Documents**: First page, middle page(s), and last page
- **Maximum Length**: Configurable via `LLM_OCR_SNIPPET_MAX_CHARS` (default: 3000 characters)

**Best Practice**: Include context from multiple sections of the document to help the LLM understand the full context.

### Temperature Setting

**Current Setting**: `temperature=0.0`

**Rationale**: 
- Ensures deterministic, consistent outputs
- Reduces variability in field extraction
- Improves reliability for production use

**Best Practice**: Use `temperature=0.0` for structured data extraction tasks.

### Response Format

**Required Format**: JSON object with canonical field names as keys

**Example**:
```json
{
  "invoice_number": "4202092525",
  "invoice_date": "2024-09-25"
}
```

**Best Practice**: 
- Request JSON output explicitly
- Validate JSON structure before parsing
- Handle malformed JSON gracefully

---

## Configuration Settings

### LLM Fallback Settings

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| **Enable LLM Fallback** | `USE_LLM_FALLBACK` | `False` | Enable/disable LLM fallback |
| **Confidence Threshold** | `LLM_LOW_CONF_THRESHOLD` | `0.75` | Threshold for triggering LLM (0.0-1.0) |
| **Cache TTL** | `LLM_CACHE_TTL_SECONDS` | `3600` | Cache entry TTL in seconds (1 hour) |
| **Cache Max Size** | `LLM_CACHE_MAX_SIZE` | `1000` | Maximum cache entries (LRU eviction) |
| **OCR Snippet Max Chars** | `LLM_OCR_SNIPPET_MAX_CHARS` | `3000` | Maximum characters in OCR snippet |

### Azure OpenAI Settings

| Setting | Environment Variable | Required | Description |
|---------|---------------------|----------|-------------|
| **Endpoint** | `AOAI_ENDPOINT` | Yes | Azure OpenAI endpoint URL |
| **API Key** | `AOAI_API_KEY` | Yes | Azure OpenAI API key |
| **Deployment Name** | `AOAI_DEPLOYMENT_NAME` | Yes | Model deployment name (e.g., "gpt-4o") |
| **API Version** | `AOAI_API_VERSION` | No | API version (default: "2024-02-15-preview") |

### Multimodal LLM Settings

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| **Enable Multimodal** | `USE_MULTIMODAL_LLM_FALLBACK` | `False` | Enable multimodal LLM for scanned PDFs |
| **Multimodal Deployment** | `AOAI_MULTIMODAL_DEPLOYMENT_NAME` | None | Dedicated multimodal deployment (optional) |
| **Max Pages** | `MULTIMODAL_MAX_PAGES` | `2` | Maximum pages to render as images |
| **Image Scale** | `MULTIMODAL_IMAGE_SCALE` | `2.0` | Image scaling factor for rendering |

### Example Configuration

```bash
# Enable LLM fallback
USE_LLM_FALLBACK=True

# Set confidence threshold (75%)
LLM_LOW_CONF_THRESHOLD=0.75

# Configure Azure OpenAI
AOAI_ENDPOINT=https://your-resource.openai.azure.com/
AOAI_API_KEY=your-api-key
AOAI_DEPLOYMENT_NAME=gpt-4o

# Configure caching (optional)
LLM_CACHE_TTL_SECONDS=3600
LLM_CACHE_MAX_SIZE=1000

# Configure OCR snippet size (optional)
LLM_OCR_SNIPPET_MAX_CHARS=3000
```

---

## Error Handling

### Retry Logic

The LLM fallback system implements exponential backoff retry logic:

- **Max Retries**: 3 retries (4 total attempts)
- **Initial Delay**: 1.0 second
- **Max Delay**: 60.0 seconds
- **Exponential Base**: 2.0

### Error Types and Handling

#### Rate Limiting (429)

**Behavior**: Always retried with exponential backoff

**Retry-After Header**: If present, used to determine delay

**Example**:
```python
if status == 429 or isinstance(call_err, RateLimitError):
    delay = min(initial_delay * (exponential_base ** attempt), max_delay)
    if retry_after:
        delay = max(delay, float(retry_after))
    await asyncio.sleep(delay)
    continue  # Retry
```

#### API Errors (500, 503)

**Behavior**: Retried with exponential backoff (up to max retries)

**Example**:
```python
elif isinstance(call_err, APIError) and attempt < max_retries:
    delay = min(initial_delay * (exponential_base ** attempt), max_delay)
    await asyncio.sleep(delay)
    continue  # Retry
```

#### Authentication Errors (401, 403)

**Behavior**: Not retried (indicates credential issue)

**Example**:
```python
# Authentication errors are logged and skipped
logger.error("LLM authentication failed: %s", call_err)
# Continue with DI-only results
```

#### Bad Request (400)

**Behavior**: Not retried (indicates request format issue)

**Example**:
```python
# Bad request errors are logged and skipped
logger.error("LLM bad request: %s", call_err)
# Continue with DI-only results
```

#### Network Errors

**Behavior**: Retried with exponential backoff

**Types**: Timeout, ConnectionError, etc.

### Partial Success Handling

The system supports partial success - if some field groups succeed and others fail, successful corrections are still applied:

```python
group_results = {
    "fields": {"success": True, "fields": ["invoice_number", "invoice_date"]},
    "addresses": {"success": False, "error": "Rate limit exceeded"}
}

# Fields group corrections are applied
# Addresses group is skipped
```

### Error Logging

All errors are logged with detailed context:

```python
logger.error(
    "LLM fallback call failed for group %s: %s. "
    "Endpoint: %s, Deployment: %s",
    grp_name, error_msg, aoai_endpoint, deployment_name,
    exc_info=True
)
```

---

## Multimodal LLM Fallback

### When Multimodal is Used

Multimodal LLM fallback is triggered when:

1. **Multimodal is Enabled**: `USE_MULTIMODAL_LLM_FALLBACK=True`
2. **PDF is Scanned**: PDF is detected as image-based (not text-based)
3. **Text-Based LLM Failed**: Text-based LLM did not improve fields (optional fallback)

### PDF Detection

The system detects scanned PDFs by:

1. Extracting text from the first page
2. Checking if text length < 50 characters
3. If true, PDF is considered scanned

```python
def _is_scanned_pdf(self, file_content: bytes) -> bool:
    pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
    first_page = pdf_reader.pages[0]
    text = first_page.extract_text()
    return text is None or len(text.strip()) < 50
```

### Image Rendering

PDF pages are rendered as base64-encoded PNG images:

- **Max Pages**: Configurable via `MULTIMODAL_MAX_PAGES` (default: 2)
- **Image Scale**: Configurable via `MULTIMODAL_IMAGE_SCALE` (default: 2.0)
- **Format**: PNG (base64-encoded)

### Multimodal Prompt Structure

The multimodal prompt includes:

1. **Text Prompt**: Same as text-based LLM (field values, confidence, OCR snippet)
2. **Image Content**: Base64-encoded PNG images of PDF pages

```python
messages = [
    {"role": "system", "content": LLM_SYSTEM_PROMPT},
    {
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}}
            for img in images
        ]
    }
]
```

### Multimodal vs Text-Based

| Feature | Text-Based | Multimodal |
|---------|-----------|------------|
| **Input** | OCR text snippet | OCR text + PDF page images |
| **Use Case** | Text-based PDFs | Scanned/image-based PDFs |
| **Cost** | Lower | Higher (more tokens) |
| **Accuracy** | Good for text PDFs | Better for scanned PDFs |
| **Deployment** | `AOAI_DEPLOYMENT_NAME` | `AOAI_MULTIMODAL_DEPLOYMENT_NAME` (optional) |

---

## Best Practices Summary

### 1. Configuration

- **Enable LLM Fallback**: Set `USE_LLM_FALLBACK=True` in production
- **Set Appropriate Threshold**: Use `LLM_LOW_CONF_THRESHOLD=0.75` (adjust based on accuracy needs)
- **Configure Caching**: Set `LLM_CACHE_TTL_SECONDS` and `LLM_CACHE_MAX_SIZE` to reduce costs

### 2. Monitoring

- **Log LLM Calls**: Monitor LLM API usage and costs
- **Track Success Rates**: Monitor `groups_succeeded` vs `groups_failed`
- **Monitor Confidence Scores**: Track confidence score improvements after LLM correction

### 3. Error Handling

- **Handle Partial Failures**: System continues with DI results if LLM fails
- **Monitor Retries**: Track retry counts for rate limiting issues
- **Set Alerts**: Alert on authentication errors (401) or bad requests (400)

### 4. Performance

- **Use Caching**: LLM responses are cached to reduce API calls
- **Group Fields Efficiently**: Fields are grouped to minimize API payload size
- **Limit OCR Snippet Size**: Use `LLM_OCR_SNIPPET_MAX_CHARS` to control prompt size

### 5. Validation

- **Validate All Suggestions**: All LLM suggestions are validated before application
- **Reject Invalid Values**: Invalid dates, amounts, etc. are rejected
- **Log Validation Errors**: Validation errors are logged for debugging

---

## Appendix: Complete System Prompt

The complete LLM system prompt is defined in `src/extraction/extraction_service.py`:

```python
LLM_SYSTEM_PROMPT = """
You are a specialized invoice extraction QA assistant for CATSA.

You receive:
- A JSON object `di_payload` that contains the extracted invoice fields and their values, using the canonical field names expected by downstream systems.
- A JSON object `field_confidence` with per-field confidence scores from the upstream extractor.
- A JSON array `low_conf_fields` listing the subset of fields that the upstream model is uncertain about.
- Optionally, a short OCR text snippet from the invoice PDF.

Your task:
1. For each field in `low_conf_fields`, decide whether the value in `di_payload` is correct.
2. If it is clearly wrong or missing, infer a corrected value using ONLY the provided JSON and OCR snippet.
3. NEVER invent fields, change field names, or guess values that are not strongly supported by the data.
4. If you cannot reliably correct a field, set it to null.
5. Output ONLY a single JSON object whose keys are exactly the field names from `low_conf_fields`, with their corrected (or null) values.
6. Do NOT include explanations, comments, or extra properties.

CANONICAL FIELD NAMES (use these EXACTLY):
Header: invoice_number, invoice_date, due_date, invoice_type, reference_number
Vendor: vendor_name, vendor_id, vendor_phone, vendor_fax, vendor_email, vendor_website, vendor_address
Vendor Tax IDs: gst_number, qst_number, pst_number, business_number
Customer: customer_name, customer_id, customer_phone, customer_email, customer_fax, bill_to_address
Remit-To: remit_to_address, remit_to_name
Contract: entity, contract_id, standing_offer_number, po_number
Dates: period_start, period_end, shipping_date, delivery_date
Financial: subtotal, discount_amount, shipping_amount, handling_fee, deposit_amount
Canadian Taxes: gst_amount, gst_rate, hst_amount, hst_rate, qst_amount, qst_rate, pst_amount, pst_rate
Total: tax_amount, total_amount, currency
Payment: payment_terms, payment_method, payment_due_upon, tax_registration_number

Formatting rules:
- Dates must be ISO 8601 date strings: "YYYY-MM-DD".
- Monetary amounts must be numeric strings, using "." as the decimal separator (e.g., "1234.56").
- Trim whitespace and normalize casing where appropriate, but do not rewrite vendor names beyond obvious OCR fixes.
- For address fields (vendor_address, bill_to_address, remit_to_address), return an object with keys: street, city, province, postal_code, country. Use null or empty for unknown subfields.
"""
```

---

**Document End**

