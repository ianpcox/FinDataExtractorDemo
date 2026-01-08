# Comprehensive Test Reports Guide

## Overview

All three extraction test suites (DI OCR, Base LLM, and Multimodal LLM) now generate comprehensive reports with:

1. **Process Flow Documentation** - Detailed step-by-step process flow
2. **False Negative Detection** - Identifies fields that should be extracted but aren't
3. **Line Items Support** - Includes line items in new table structure
4. **Higher-Level Data Capture** - All invoice fields except line items
5. **Confusion Matrix Analysis** - Per-PDF, per-field, and overall confusion matrices
6. **Comprehensive CSV Outputs** - Field-by-field data with false negative flags

## Test Scripts

### 1. DI OCR Test
**Script**: `run_di_ocr_with_false_negative_detection.py`

**Process Flow**:
1. Preprocessing (PDF loading)
2. Document Intelligence OCR
3. Field Extraction (includes line items)
4. Confidence Calculation
5. Line Items Processing
6. Extraction Detection
7. False Negative Detection

**Outputs**:
- `di_ocr_extraction_with_false_negatives.csv` - Combined results with false negative flags
- `di_ocr_test_report_with_false_negatives.md` - Comprehensive report
- `false_negatives_report.csv` - Detailed false negative analysis
- Confusion matrix CSVs and report

### 2. Base LLM Test
**Script**: `run_llm_extraction_with_false_negative_detection.py`

**Process Flow**:
1. Preprocessing (PDF loading)
2. Document Intelligence OCR
3. Field Extraction (includes line items)
4. Confidence Calculation
5. Low-Confidence Field Identification
6. Base LLM Fallback
7. Line Items Processing
8. Extraction Detection
9. False Negative Detection

**Outputs**:
- `llm_extraction_with_false_negatives.csv` - Combined results with false negative flags
- `llm_extraction_test_report_with_false_negatives.md` - Comprehensive report
- `llm_false_negatives_report.csv` - Detailed false negative analysis
- Confusion matrix CSVs and report

### 3. Multimodal LLM Test
**Script**: `run_multimodal_llm_extraction_with_false_negative_detection.py`

**Process Flow**:
1. Preprocessing (PDF loading)
2. Document Intelligence OCR
3. Scanned PDF Detection
4. Field Extraction (includes line items)
5. Confidence Calculation
6. Low-Confidence Field Identification
7. Multimodal LLM Fallback (if scanned)
8. Text-Based LLM Fallback (if multimodal fails)
9. Line Items Processing
10. Extraction Detection
11. False Negative Detection

**Outputs**:
- `multimodal_llm_extraction_with_false_negatives.csv` - Combined results with false negative flags
- `multimodal_llm_extraction_test_report_with_false_negatives.md` - Comprehensive report
- `multimodal_llm_false_negatives_report.csv` - Detailed false negative analysis
- Confusion matrix CSVs and report

## Data Structure

### Higher-Level Invoice Fields

All tests capture the following invoice-level fields (everything except line items):

**Header Fields**:
- invoice_number, invoice_date, due_date, invoice_type, reference_number

**Vendor Fields**:
- vendor_name, vendor_id, vendor_phone, vendor_fax, vendor_email, vendor_website, vendor_address

**Vendor Tax IDs**:
- gst_number, qst_number, pst_number, business_number

**Customer Fields**:
- customer_name, customer_id, customer_phone, customer_email, customer_fax, bill_to_address

**Remit-To Fields**:
- remit_to_address, remit_to_name

**Contract Fields**:
- entity, contract_id, standing_offer_number, po_number

**Date Fields**:
- period_start, period_end, shipping_date, delivery_date

**Financial Fields**:
- subtotal, discount_amount, shipping_amount, handling_fee, deposit_amount

**Canadian Tax Fields**:
- gst_amount, gst_rate, hst_amount, hst_rate, qst_amount, qst_rate, pst_amount, pst_rate

**Total Fields**:
- tax_amount, total_amount, currency

**Payment Fields**:
- payment_terms, payment_method, payment_due_upon, tax_registration_number

### Line Items Structure

All tests capture line items in the new table structure format:

```python
{
    "line_number": int,
    "description": str,
    "quantity": Decimal,
    "unit_price": Decimal,
    "amount": Decimal,
    "tax_amount": Decimal,
    "gst_amount": Decimal,
    "pst_amount": Decimal,
    "qst_amount": Decimal,
    "confidence": float
}
```

Line items are:
- Extracted from Document Intelligence `Items` field
- Structured for the `line_items` table
- Included in CSV outputs with `field_category: "line_item"`
- Reported separately in markdown reports

## CSV Output Structure

### Combined CSV Files

Each test generates a combined CSV with:

**Columns**:
- `pdf_name`: PDF file name
- `field_name`: Field name (or `line_item_N` for line items)
- `field_category`: "invoice_field" or "line_item"
- `extracted`: Boolean indicating if field was extracted
- `value`: Field value (truncated to 100 chars for invoice fields)
- `confidence`: Confidence score
- `confidence_category`: "high", "medium", "low", or "none"
- `false_negative`: Boolean flag for false negatives
- `value_type`: Type of the value
- `di_field_sources`: DI field names that mapped to this field (DI OCR only)
- `extracted_by_di`: Boolean (Base LLM and Multimodal LLM)
- `extracted_by_llm`: Boolean (Base LLM only)
- `extracted_by_multimodal`: Boolean (Multimodal LLM only)
- `extracted_by_text_llm`: Boolean (Multimodal LLM only)
- `line_number`: Line item number (for line items)
- `line_item_amount`: Line item amount (for line items)
- `line_item_quantity`: Line item quantity (for line items)
- `line_item_unit_price`: Line item unit price (for line items)

## Running the Tests

### DI OCR Test
```bash
python run_di_ocr_with_false_negative_detection.py
```

### Base LLM Test
```bash
python run_llm_extraction_with_false_negative_detection.py
```

### Multimodal LLM Test
```bash
python run_multimodal_llm_extraction_with_false_negative_detection.py
```

## Report Sections

All reports include:

1. **Process Flow** - Detailed step-by-step documentation
2. **Executive Summary** - Overall statistics
3. **Results by PDF** - Per-PDF breakdown
4. **False Negatives Analysis** - By field and by PDF
5. **Line Items Summary** - Line items structure and statistics
6. **Process Steps Log** - Timestamped execution log
7. **Confusion Matrix Analysis** - Links to detailed confusion matrices

## Key Features

### ✅ Comprehensive Coverage
- All three tests now match the DI OCR test structure
- Process flow documentation for each step
- False negative detection and analysis
- Confusion matrix generation

### ✅ Line Items Support
- Line items extracted and structured
- New table format ready
- Separate reporting in CSV and markdown
- Includes all line item fields (amount, taxes, etc.)

### ✅ Higher-Level Data Capture
- All invoice fields captured
- Confidence scores tracked
- Source tracking (DI, LLM, Multimodal)
- Field-by-field analysis

### ✅ Consistent Structure
- All three tests follow the same pattern
- Same CSV column structure
- Same report sections
- Same analysis depth

## Comparison

| Feature | DI OCR | Base LLM | Multimodal LLM |
|---------|--------|----------|----------------|
| Process Flow | ✅ | ✅ | ✅ |
| False Negative Detection | ✅ | ✅ | ✅ |
| Line Items | ✅ | ✅ | ✅ |
| Higher-Level Fields | ✅ | ✅ | ✅ |
| Confusion Matrices | ✅ | ✅ | ✅ |
| CSV Outputs | ✅ | ✅ | ✅ |
| Markdown Reports | ✅ | ✅ | ✅ |
| LLM Statistics | ❌ | ✅ | ✅ |
| Multimodal Statistics | ❌ | ❌ | ✅ |
| Scanned PDF Detection | ❌ | ❌ | ✅ |

## Next Steps

1. Run all three tests on the same set of PDFs
2. Compare results across extraction methods
3. Analyze which method performs best for different field types
4. Use line items data for aggregation validation
5. Use false negative analysis to improve extraction
