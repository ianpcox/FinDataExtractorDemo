# Multimodal LLM Behavior Documentation

**Last Updated:** 2026-01-07  
**Version:** 1.0

---

## Table of Contents

1. [Overview](#overview)
2. [When Multimodal LLM Fallback is Triggered](#when-multimodal-llm-fallback-is-triggered)
3. [PDF Detection Logic](#pdf-detection-logic)
4. [Image Rendering Configuration](#image-rendering-configuration)
5. [Confidence Score Updates](#confidence-score-updates)
6. [Field Formatting Rules](#field-formatting-rules)
7. [Multimodal Prompt Structure](#multimodal-prompt-structure)
8. [Best Practices](#best-practices)
9. [Configuration Settings](#configuration-settings)
10. [Error Handling](#error-handling)
11. [Image Rendering Details](#image-rendering-details)

---

## Overview

The Multimodal LLM fallback system extends the text-based LLM fallback by providing image-based analysis for scanned PDFs. When a PDF is detected as image-based (scanned), the system renders PDF pages as images and sends them to Azure OpenAI's multimodal model (GPT-4o with vision) along with the OCR text, enabling the LLM to "see" the document and extract fields more accurately.

### Key Features

- **Automatic PDF Detection**: Automatically detects scanned/image-based PDFs vs text-based PDFs
- **Image Rendering**: Converts PDF pages to base64-encoded PNG images for LLM input
- **Multimodal Analysis**: LLM analyzes both OCR text and visual document layout
- **Fallback Strategy**: Falls back to text-based LLM if multimodal fails or PDF is text-based
- **Same Confidence Logic**: Uses the same dynamic confidence calculation as text-based LLM
- **Same Field Validation**: Uses the same field validation rules as text-based LLM

### Use Cases

Multimodal LLM is particularly effective for:

- **Scanned PDFs**: Documents that are image-based (scanned paper invoices)
- **Poor OCR Quality**: When Document Intelligence OCR produces low-confidence results
- **Complex Layouts**: Documents with complex formatting that benefits from visual analysis
- **Handwritten Text**: Documents with handwritten annotations or signatures
- **Low-Confidence Fields**: When text-based LLM doesn't improve field confidence

---

## When Multimodal LLM Fallback is Triggered

### Primary Trigger Conditions

Multimodal LLM fallback is triggered when **all** of the following conditions are met:

1. **Multimodal LLM Fallback is Enabled**: `USE_MULTIMODAL_LLM_FALLBACK` setting must be `True`
2. **Text-Based LLM Fallback is Enabled**: `USE_LLM_FALLBACK` setting must be `True`
3. **Azure OpenAI is Configured**: Valid credentials must be present:
   - `AOAI_ENDPOINT`
   - `AOAI_API_KEY`
   - `AOAI_DEPLOYMENT_NAME` or `AOAI_MULTIMODAL_DEPLOYMENT_NAME`
4. **PDF is Detected as Scanned**: PDF must be detected as image-based (see [PDF Detection Logic](#pdf-detection-logic))
5. **Low-Confidence Fields Exist**: At least one field has confidence below `LLM_LOW_CONF_THRESHOLD` (default: 0.75)
6. **Image Rendering Succeeds**: PDF pages must be successfully rendered as images
7. **Document Intelligence Extraction Completed**: DI extraction must have completed successfully

### Trigger Priority

The system uses the following priority order:

1. **Scanned PDF + Multimodal Enabled**: Use multimodal LLM first
2. **Text-Based PDF or Multimodal Disabled**: Use text-based LLM
3. **Multimodal Failed + Text-Based Available**: Fall back to text-based LLM
4. **All LLM Failed**: Continue with DI-only results

### Fallback Strategy

```python
if is_scanned and use_multimodal:
    # Try multimodal LLM first
    llm_result = await _run_multimodal_fallback(...)
else:
    # Try text-based LLM first
    llm_result = await _run_low_confidence_fallback(...)
    
    # If text-based didn't improve fields and multimodal is enabled, try multimodal
    if llm_result.get("groups_succeeded", 0) == 0 and use_multimodal:
        multimodal_result = await _run_multimodal_fallback(...)
        if multimodal_result.get("groups_succeeded", 0) > 0:
            llm_result = multimodal_result
```

### When Multimodal LLM Fallback is NOT Triggered

Multimodal LLM fallback is **skipped** in the following scenarios:

1. **Multimodal Disabled**: `USE_MULTIMODAL_LLM_FALLBACK=False`
2. **PDF is Text-Based**: PDF is detected as text-based (not scanned)
3. **PyMuPDF Not Available**: PyMuPDF library is not installed (required for image rendering)
4. **Image Rendering Failed**: PDF pages could not be rendered as images
5. **No Images Generated**: Image rendering returned empty list
6. **Azure OpenAI Not Configured**: Missing required credentials
7. **No Low-Confidence Fields**: All fields have confidence >= `LLM_LOW_CONF_THRESHOLD`

---

## PDF Detection Logic

### Detection Method

The system detects scanned PDFs by analyzing the first page of the PDF:

```python
def _is_scanned_pdf(self, file_content: bytes) -> bool:
    """Detect if PDF is primarily scanned/images (vs text-based)."""
    try:
        import PyPDF2
        pdf_file = BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        if len(pdf_reader.pages) == 0:
            return False
        first_page = pdf_reader.pages[0]
        text = first_page.extract_text()
        return text is None or len(text.strip()) < 50
    except Exception:
        logger.debug("Could not determine if PDF is scanned, assuming text-based")
        return False
```

### Detection Criteria

A PDF is considered **scanned** if:

- **No text extracted**: `text is None`
- **Minimal text**: `len(text.strip()) < 50` characters

A PDF is considered **text-based** if:

- **Text extracted**: `text is not None`
- **Sufficient text**: `len(text.strip()) >= 50` characters

### Detection Limitations

- **First Page Only**: Detection is based on the first page only
- **Heuristic-Based**: Uses a simple heuristic (text length), not ML-based detection
- **False Positives**: Text-based PDFs with very little text (< 50 chars) may be misclassified
- **False Negatives**: Scanned PDFs with good OCR text may be misclassified as text-based

### Manual Override

Currently, there is no manual override for PDF detection. The system automatically detects based on the heuristic above.

---

## Image Rendering Configuration

### Image Rendering Process

The image rendering process converts PDF pages to base64-encoded PNG images:

```python
def _render_multimodal_images(self, file_content: bytes) -> List[str]:
    """Render a small set of PDF pages as base64 PNGs for multimodal prompts."""
    try:
        import fitz  # PyMuPDF
    except Exception:
        logger.warning("PyMuPDF not available; skipping multimodal image rendering.")
        return []
    
    max_pages = max(1, int(getattr(settings, "MULTIMODAL_MAX_PAGES", 2)))
    scale = float(getattr(settings, "MULTIMODAL_IMAGE_SCALE", 2.0))
    
    pdf_doc = fitz.open(stream=file_content, filetype="pdf")
    images: List[str] = []
    
    for page_num in range(min(len(pdf_doc), max_pages)):
        page = pdf_doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
        img_bytes = pix.tobytes("png")
        images.append(base64.b64encode(img_bytes).decode("utf-8"))
    
    pdf_doc.close()
    return images
```

### Configuration Settings

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| **Max Pages** | `MULTIMODAL_MAX_PAGES` | `2` | Maximum number of PDF pages to render as images |
| **Image Scale** | `MULTIMODAL_IMAGE_SCALE` | `2.0` | Image scaling factor (higher = better quality, larger size) |

### Image Format

- **Format**: PNG (Portable Network Graphics)
- **Encoding**: Base64-encoded strings
- **Data URI**: `data:image/png;base64,{base64_string}`

### Image Quality vs Size Trade-off

| Scale Factor | Quality | Size | Use Case |
|--------------|---------|------|----------|
| `1.0` | Low | Small | Fast processing, low quality |
| `2.0` | Medium | Medium | **Default** - Balanced quality/size |
| `3.0` | High | Large | High quality, slower processing |
| `4.0` | Very High | Very Large | Maximum quality, may hit API limits |

### Page Selection

- **First Pages**: Always renders the first N pages (where N = `MULTIMODAL_MAX_PAGES`)
- **No Page Selection**: Currently, there is no intelligent page selection (e.g., most relevant pages)
- **Multi-Page Documents**: For documents with many pages, only the first few pages are rendered

### Dependencies

- **PyMuPDF (fitz)**: Required for PDF to image conversion
  - Install: `pip install PyMuPDF`
  - If not available, multimodal LLM fallback is skipped

---

## Confidence Score Updates

Multimodal LLM uses the **same dynamic confidence calculation** as text-based LLM. See [LLM_BEHAVIOR_DOCUMENTATION.md](LLM_BEHAVIOR_DOCUMENTATION.md#confidence-score-updates) for details.

### Key Points

- **Same Logic**: Uses `_calculate_llm_confidence()` method
- **Context-Aware**: Confidence based on whether field was blank, corrected, or confirmed
- **Original Confidence Adjustment**: Adjusts based on original confidence score
- **Critical Field Boost**: Critical fields get additional confidence boost when filled from blank

### Confidence Ranges

| Scenario | Base Confidence | Rationale |
|----------|----------------|-----------|
| **LLM filled blank field** | 0.90 | High confidence - Multimodal LLM extracted missing data |
| **LLM corrected wrong value** | 0.80 | Medium-high confidence - Multimodal LLM fixed existing data |
| **LLM confirmed existing value** | 0.75 | Medium confidence - Multimodal LLM validated existing value |
| **LLM set to null/blank** | 0.70 | Lower confidence - Multimodal LLM intentionally cleared field |

---

## Field Formatting Rules

Multimodal LLM uses the **same field formatting rules** as text-based LLM. See [LLM_BEHAVIOR_DOCUMENTATION.md](LLM_BEHAVIOR_DOCUMENTATION.md#field-formatting-rules) for details.

### Key Points

- **Same Rules**: Uses the same formatting rules as text-based LLM
- **Same Validation**: Uses `_validate_llm_suggestion()` for validation
- **Same Field Types**: Supports all 57 canonical fields

### Formatting Summary

- **Dates**: ISO 8601 format (`YYYY-MM-DD`)
- **Amounts**: Numeric strings with "." as decimal separator
- **Addresses**: JSON objects with `street`, `city`, `province`, `postal_code`, `country`
- **Tax Rates**: Decimal values between 0.0 and 1.0
- **Currency**: ISO 4217 currency codes (3-letter uppercase)

---

## Multimodal Prompt Structure

### System Prompt

Multimodal LLM uses the **same system prompt** as text-based LLM (`LLM_SYSTEM_PROMPT`). See [LLM_BEHAVIOR_DOCUMENTATION.md](LLM_BEHAVIOR_DOCUMENTATION.md#llm-prompt-best-practices) for details.

### User Prompt Structure

The multimodal user prompt includes both text and images:

```python
messages = [
    {"role": "system", "content": LLM_SYSTEM_PROMPT},
    {
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},  # Text prompt (same as text-based LLM)
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}}  # Image 1
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}}  # Image 2 (if multiple pages)
            # ... more images
        ]
    }
]
```

### Text Prompt Content

The text prompt includes:

1. **Low-Confidence Fields**: List of fields to evaluate
2. **Field Values**: Current values from DI extraction
3. **Field Confidence Scores**: Confidence scores for each field
4. **OCR Snippet**: Relevant text from the document (beginning, middle, end)

### Image Content

The image content includes:

1. **Base64-Encoded PNG Images**: Rendered PDF pages
2. **Data URI Format**: `data:image/png;base64,{base64_string}`
3. **Multiple Pages**: Up to `MULTIMODAL_MAX_PAGES` images (default: 2)

### Prompt Example

```json
{
  "role": "user",
  "content": [
    {
      "type": "text",
      "text": "{\n  \"low_confidence_fields\": [\"invoice_number\", \"invoice_date\"],\n  \"fields\": {\n    \"invoice_number\": \"4202092525\",\n    \"invoice_date\": \"2025-09-25\"\n  },\n  \"field_confidence\": {\n    \"invoice_number\": 0.65,\n    \"invoice_date\": 0.70\n  },\n  \"ocr_snippet\": \"INVOICE\\nInvoice #: 4202092525\\nDate: September 25, 2024\\n...\"\n}"
    },
    {
      "type": "image_url",
      "image_url": {
        "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
      }
    },
    {
      "type": "image_url",
      "image_url": {
        "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
      }
    }
  ]
}
```

---

## Best Practices

### 1. Configuration

- **Enable Multimodal**: Set `USE_MULTIMODAL_LLM_FALLBACK=True` for scanned PDF processing
- **Install PyMuPDF**: Ensure `PyMuPDF` is installed: `pip install PyMuPDF`
- **Set Appropriate Scale**: Use `MULTIMODAL_IMAGE_SCALE=2.0` (default) for balanced quality/size
- **Limit Pages**: Use `MULTIMODAL_MAX_PAGES=2` (default) to control API costs

### 2. PDF Detection

- **Verify Detection**: Check logs to verify PDFs are correctly detected as scanned
- **Manual Review**: Review false positives/negatives and adjust detection logic if needed
- **Test with Sample PDFs**: Test with both scanned and text-based PDFs to verify detection

### 3. Image Rendering

- **Monitor Rendering Failures**: Check logs for image rendering errors
- **Verify PyMuPDF**: Ensure PyMuPDF is installed and working
- **Test with Various PDFs**: Test with different PDF formats and sizes

### 4. Cost Management

- **Limit Pages**: Use `MULTIMODAL_MAX_PAGES` to limit number of images sent
- **Optimize Scale**: Use lower `MULTIMODAL_IMAGE_SCALE` to reduce image size (if quality allows)
- **Monitor API Usage**: Track multimodal LLM API usage and costs
- **Use Caching**: LLM responses are cached to reduce duplicate API calls

### 5. Error Handling

- **Graceful Degradation**: System falls back to text-based LLM if multimodal fails
- **Monitor Errors**: Check logs for multimodal-specific errors
- **Handle PyMuPDF Errors**: Ensure PyMuPDF errors don't crash the system

### 6. Performance

- **Image Rendering Time**: Image rendering adds processing time (typically 1-3 seconds)
- **API Response Time**: Multimodal API calls may take longer than text-based (due to image processing)
- **Total Processing Time**: Expect 60-90 seconds for full extraction with multimodal LLM

---

## Configuration Settings

### Multimodal LLM Settings

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| **Enable Multimodal** | `USE_MULTIMODAL_LLM_FALLBACK` | `False` | Enable/disable multimodal LLM fallback |
| **Multimodal Deployment** | `AOAI_MULTIMODAL_DEPLOYMENT_NAME` | None | Dedicated multimodal deployment (optional, uses `AOAI_DEPLOYMENT_NAME` if not set) |
| **Max Pages** | `MULTIMODAL_MAX_PAGES` | `2` | Maximum number of PDF pages to render as images |
| **Image Scale** | `MULTIMODAL_IMAGE_SCALE` | `2.0` | Image scaling factor for rendering (higher = better quality, larger size) |

### Azure OpenAI Settings (Shared with Text-Based LLM)

| Setting | Environment Variable | Required | Description |
|---------|---------------------|----------|-------------|
| **Endpoint** | `AOAI_ENDPOINT` | Yes | Azure OpenAI endpoint URL |
| **API Key** | `AOAI_API_KEY` | Yes | Azure OpenAI API key |
| **Deployment Name** | `AOAI_DEPLOYMENT_NAME` | Yes* | Model deployment name (used if `AOAI_MULTIMODAL_DEPLOYMENT_NAME` not set) |
| **API Version** | `AOAI_API_VERSION` | No | API version (default: "2024-02-15-preview") |

*Required if `AOAI_MULTIMODAL_DEPLOYMENT_NAME` is not set

### Example Configuration

```bash
# Enable multimodal LLM fallback
USE_MULTIMODAL_LLM_FALLBACK=True

# Configure Azure OpenAI (shared with text-based LLM)
AOAI_ENDPOINT=https://your-resource.openai.azure.com/
AOAI_API_KEY=your-api-key
AOAI_DEPLOYMENT_NAME=gpt-4o

# Optional: Dedicated multimodal deployment
AOAI_MULTIMODAL_DEPLOYMENT_NAME=gpt-4o-vision

# Configure image rendering (optional)
MULTIMODAL_MAX_PAGES=2
MULTIMODAL_IMAGE_SCALE=2.0
```

---

## Error Handling

### Image Rendering Errors

#### PyMuPDF Not Available

**Error**: `PyMuPDF not available; skipping multimodal image rendering.`

**Behavior**: 
- Multimodal LLM fallback is skipped
- Falls back to text-based LLM (if enabled)
- Extraction continues with DI-only results

**Resolution**: Install PyMuPDF: `pip install PyMuPDF`

#### PDF Open Failure

**Error**: `Failed to open PDF for multimodal rendering: {error}`

**Behavior**:
- Image rendering returns empty list
- Multimodal LLM fallback is skipped
- Falls back to text-based LLM (if enabled)

**Resolution**: Check PDF file integrity, ensure PDF is valid

#### Image Rendering Exception

**Error**: Exception during image rendering (e.g., memory error, format error)

**Behavior**:
- Exception is caught and logged
- Image rendering returns empty list
- Multimodal LLM fallback is skipped
- Falls back to text-based LLM (if enabled)

**Resolution**: Check PDF format, reduce `MULTIMODAL_MAX_PAGES` or `MULTIMODAL_IMAGE_SCALE`

### Multimodal API Errors

Multimodal LLM uses the **same error handling** as text-based LLM. See [LLM_BEHAVIOR_DOCUMENTATION.md](LLM_BEHAVIOR_DOCUMENTATION.md#error-handling) for details.

#### Rate Limiting (429)

**Behavior**: Retries with exponential backoff (same as text-based LLM)

#### API Failures (500, 503)

**Behavior**: Retries with exponential backoff (same as text-based LLM)

#### Network Timeouts

**Behavior**: Retries with exponential backoff (same as text-based LLM)

#### Invalid JSON Responses

**Behavior**: Logs error, skips group, continues with other groups

### Fallback Strategy

The system implements a **graceful fallback strategy**:

1. **Multimodal LLM Fails**: Falls back to text-based LLM (if enabled)
2. **Text-Based LLM Fails**: Falls back to DI-only results
3. **All LLM Fails**: Continues with DI-only results (extraction still succeeds)

### Error Logging

All errors are logged with detailed context:

```python
logger.error(
    "Multimodal fallback call failed for group %s: %s. "
    "Endpoint: %s, Deployment: %s",
    grp_name, error_msg, aoai_endpoint, deployment_name,
    exc_info=True
)
```

---

## Image Rendering Details

### Rendering Process

1. **PDF Opening**: Opens PDF using PyMuPDF (`fitz.open()`)
2. **Page Iteration**: Iterates through first N pages (N = `MULTIMODAL_MAX_PAGES`)
3. **Pixmap Generation**: Generates pixmap for each page with scaling
4. **PNG Conversion**: Converts pixmap to PNG bytes
5. **Base64 Encoding**: Encodes PNG bytes as base64 string
6. **Data URI Creation**: Creates data URI for LLM input

### Technical Details

- **Library**: PyMuPDF (fitz) - Fast PDF rendering library
- **Format**: PNG (lossless compression)
- **Scaling**: Uses `fitz.Matrix(scale, scale)` for image scaling
- **Encoding**: Base64 encoding for data URI format
- **Memory**: Images are held in memory during processing

### Performance Considerations

- **Rendering Time**: ~0.5-2 seconds per page (depends on page complexity)
- **Image Size**: ~500KB-2MB per page (depends on scale factor and page content)
- **Memory Usage**: Images are held in memory until LLM call completes
- **API Payload**: Larger payloads due to base64-encoded images

### Optimization Tips

1. **Reduce Pages**: Lower `MULTIMODAL_MAX_PAGES` to reduce rendering time and API payload
2. **Lower Scale**: Reduce `MULTIMODAL_IMAGE_SCALE` to reduce image size (if quality allows)
3. **Cache Images**: Consider caching rendered images (not currently implemented)
4. **Selective Rendering**: Render only pages with low-confidence fields (not currently implemented)

---

## Comparison: Multimodal vs Text-Based LLM

| Feature | Text-Based LLM | Multimodal LLM |
|---------|---------------|----------------|
| **Input** | OCR text snippet | OCR text snippet + PDF page images |
| **Use Case** | Text-based PDFs | Scanned/image-based PDFs |
| **Detection** | N/A | Automatic PDF detection |
| **Dependencies** | None | PyMuPDF (fitz) |
| **Cost** | Lower | Higher (more tokens due to images) |
| **Processing Time** | ~10-30 seconds | ~60-90 seconds |
| **Accuracy** | Good for text PDFs | Better for scanned PDFs |
| **Image Rendering** | Not required | Required (PDF → PNG conversion) |
| **Deployment** | `AOAI_DEPLOYMENT_NAME` | `AOAI_MULTIMODAL_DEPLOYMENT_NAME` (optional) |

---

## Best Practices Summary

### 1. Configuration

- **Enable Multimodal**: Set `USE_MULTIMODAL_LLM_FALLBACK=True` for scanned PDF processing
- **Install PyMuPDF**: Ensure `PyMuPDF` is installed: `pip install PyMuPDF`
- **Set Appropriate Scale**: Use `MULTIMODAL_IMAGE_SCALE=2.0` (default) for balanced quality/size
- **Limit Pages**: Use `MULTIMODAL_MAX_PAGES=2` (default) to control API costs

### 2. Monitoring

- **Log Multimodal Calls**: Monitor multimodal LLM API usage and costs
- **Track Success Rates**: Monitor `groups_succeeded` vs `groups_failed` for multimodal
- **Monitor Image Rendering**: Check logs for image rendering errors
- **Verify PDF Detection**: Ensure PDFs are correctly detected as scanned

### 3. Error Handling

- **Handle PyMuPDF Errors**: Ensure PyMuPDF errors don't crash the system
- **Monitor Fallbacks**: Track when multimodal falls back to text-based LLM
- **Set Alerts**: Alert on image rendering failures or multimodal API errors

### 4. Performance

- **Optimize Image Size**: Use appropriate `MULTIMODAL_IMAGE_SCALE` to balance quality/size
- **Limit Pages**: Use `MULTIMODAL_MAX_PAGES` to control processing time
- **Monitor API Costs**: Track multimodal LLM API usage (images increase token usage)

### 5. Testing

- **Test with Scanned PDFs**: Verify multimodal LLM works with actual scanned PDFs
- **Test PDF Detection**: Verify PDF detection logic works correctly
- **Test Image Rendering**: Verify image rendering works with various PDF formats
- **Test Fallback**: Verify fallback to text-based LLM works when multimodal fails

---

## Appendix: Complete Multimodal Fallback Flow

```
1. Document Intelligence Extraction
   ↓
2. Identify Low-Confidence Fields
   ↓
3. Check if Multimodal is Enabled
   ↓
4. Detect if PDF is Scanned
   ├─ Yes → Continue to multimodal
   └─ No → Use text-based LLM
   ↓
5. Render PDF Pages as Images
   ├─ Success → Continue to multimodal
   └─ Failure → Fall back to text-based LLM
   ↓
6. Call Multimodal LLM API
   ├─ Success → Apply corrections
   └─ Failure → Fall back to text-based LLM
   ↓
7. Apply LLM Corrections
   ↓
8. Update Confidence Scores
   ↓
9. Save to Database
```

---

**Document End**

