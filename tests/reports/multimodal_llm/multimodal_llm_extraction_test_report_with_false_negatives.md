# Multimodal LLM Extraction Test Report with False Negative Detection

**Generated:** 2026-01-08 19:55:46 UTC
**PDFs Tested:** 5

---

## Process Flow

This test executes the following steps in the end-to-end extraction process:

### 1. Preprocessing
- **Step:** PDF file loading and validation
- **Description:** Load PDF file from disk, validate file format and size
- **Status:** ✅ Executed in test

### 2. Document Intelligence OCR
- **Step:** Azure Document Intelligence API call
- **Description:** Send PDF to Azure DI service for OCR and field extraction
- **Status:** ✅ Executed in test (real Azure DI API)
- **Output:** Raw DI analysis result with fields and confidence scores

### 3. Scanned PDF Detection
- **Step:** Determine if PDF is scanned (image-based)
- **Description:** Analyze PDF structure to detect if it's a scanned document
- **Status:** ✅ Executed in test
- **Output:** Boolean flag indicating if PDF is scanned

### 4. Field Extraction
- **Step:** Map DI fields to canonical schema
- **Description:** Extract fields from DI result using FieldExtractor
- **Status:** ✅ Executed in test
- **Output:** Invoice object with canonical fields populated
- **Includes:** Higher-level invoice fields AND line items (new table structure)

### 5. Confidence Calculation
- **Step:** Calculate field-level and overall confidence
- **Description:** Analyze confidence scores from DI, categorize as high/medium/low
- **Status:** ✅ Executed in test
- **Output:** Confidence scores and categories for each field

### 6. Low-Confidence Field Identification
- **Step:** Identify fields requiring LLM enhancement
- **Description:** Find fields with confidence < threshold or missing values
- **Status:** ✅ Executed in test
- **Output:** List of low-confidence fields for LLM processing

### 7. Multimodal LLM Fallback (if scanned)
- **Step:** Multimodal LLM extraction with image rendering
- **Description:** Use Azure OpenAI Vision API to extract/improve fields from PDF images
- **Status:** ✅ Executed in test (if PDF is scanned, real Azure OpenAI Vision API)
- **Output:** Enhanced field values with improved confidence
- **Image Rendering:** PDF pages converted to base64 images for Vision API

### 8. Text-Based LLM Fallback (if multimodal fails or not scanned)
- **Step:** Text-based LLM extraction
- **Description:** Use Azure OpenAI to extract/improve fields from DI text
- **Status:** ✅ Executed in test (if needed, real Azure OpenAI API)
- **Output:** Enhanced field values with improved confidence

### 9. Line Items Processing
- **Step:** Extract and structure line items
- **Description:** Process line items from DI, structure for new table format
- **Status:** ✅ Executed in test
- **Output:** Line items array ready for line_items table
- **Structure:** Includes line_number, description, quantity, unit_price, amount, taxes, etc.

### 10. Extraction Detection
- **Step:** Determine if fields are extracted
- **Description:** Check if field has non-empty value based on type
- **Status:** ✅ Executed in test
- **Output:** Boolean flag for each field indicating extraction status

### 11. False Negative Detection
- **Step:** Identify potential false negatives
- **Description:** Find fields marked as not extracted but have values
- **Status:** ✅ Executed in test
- **Output:** List of potential false negatives with analysis

### Steps NOT Executed in This Test
- ❌ **Database Persistence:** Not executed (standalone test)
- ❌ **Validation:** Not executed (standalone test)
- ❌ **HITL Review:** Not executed (standalone test)

---

## Executive Summary

- **Total PDFs Tested:** 5
- **Scanned PDFs:** 0
- **Total Fields Available:** 265
- **Total Fields Extracted:** 106
- **Overall Extraction Rate:** 40.0%
- **Total Line Items Extracted:** 399
- **False Negatives Detected:** 159

---

## Results by PDF

### ACC012 4202092525.pdf

- **Is Scanned:** ❌ No
- **Extraction Rate:** 47.2%
- **Fields Extracted:** 25/53
- **Line Items:** 1
- **Overall Confidence:** 0.895
- **Multimodal LLM Triggered:** ❌ No
- **Text LLM Triggered:** ✅ Yes
- **Text LLM Success:** ✅
- **False Negatives:** 28

  False negative fields:
    - `deposit_amount`: N/A (confidence: N/A)
    - `business_number`: N/A (confidence: N/A)
    - `contract_id`: N/A (confidence: N/A)
    - `currency`: N/A (confidence: N/A)
    - `customer_email`: N/A (confidence: N/A)
    - `customer_fax`: N/A (confidence: N/A)
    - `customer_id`: N/A (confidence: N/A)
    - `customer_phone`: N/A (confidence: N/A)
    - `delivery_date`: N/A (confidence: N/A)
    - `discount_amount`: N/A (confidence: N/A)
    - `entity`: N/A (confidence: N/A)
    - `handling_fee`: N/A (confidence: N/A)
    - `hst_amount`: N/A (confidence: N/A)
    - `hst_rate`: N/A (confidence: N/A)
    - `invoice_type`: N/A (confidence: N/A)
    - `payment_due_upon`: N/A (confidence: N/A)
    - `payment_method`: N/A (confidence: N/A)
    - `period_end`: N/A (confidence: N/A)
    - `qst_amount`: N/A (confidence: N/A)
    - `qst_number`: N/A (confidence: N/A)
    - `qst_rate`: N/A (confidence: N/A)
    - `reference_number`: N/A (confidence: N/A)
    - `shipping_amount`: N/A (confidence: N/A)
    - `shipping_date`: N/A (confidence: N/A)
    - `standing_offer_number`: N/A (confidence: N/A)
    - `tax_registration_number`: N/A (confidence: N/A)
    - `vendor_id`: N/A (confidence: N/A)
    - `vendor_website`: N/A (confidence: N/A)

---

### ANA005 90443097.pdf

- **Is Scanned:** ❌ No
- **Extraction Rate:** 45.3%
- **Fields Extracted:** 24/53
- **Line Items:** 5
- **Overall Confidence:** 0.892
- **Multimodal LLM Triggered:** ❌ No
- **Text LLM Triggered:** ✅ Yes
- **Text LLM Success:** ✅
- **False Negatives:** 29

  False negative fields:
    - `contract_id`: N/A (confidence: N/A)
    - `customer_email`: N/A (confidence: N/A)
    - `customer_fax`: N/A (confidence: N/A)
    - `customer_phone`: N/A (confidence: N/A)
    - `delivery_date`: N/A (confidence: N/A)
    - `deposit_amount`: N/A (confidence: N/A)
    - `discount_amount`: N/A (confidence: N/A)
    - `handling_fee`: N/A (confidence: N/A)
    - `hst_amount`: N/A (confidence: N/A)
    - `hst_rate`: N/A (confidence: N/A)
    - `invoice_type`: N/A (confidence: N/A)
    - `payment_due_upon`: N/A (confidence: N/A)
    - `payment_method`: N/A (confidence: N/A)
    - `period_end`: N/A (confidence: N/A)
    - `period_start`: N/A (confidence: N/A)
    - `pst_amount`: N/A (confidence: N/A)
    - `pst_number`: N/A (confidence: N/A)
    - `pst_rate`: N/A (confidence: N/A)
    - `qst_amount`: N/A (confidence: N/A)
    - `qst_number`: N/A (confidence: N/A)
    - `qst_rate`: N/A (confidence: N/A)
    - `reference_number`: N/A (confidence: N/A)
    - `shipping_amount`: N/A (confidence: N/A)
    - `shipping_date`: N/A (confidence: N/A)
    - `tax_registration_number`: N/A (confidence: N/A)
    - `vendor_email`: N/A (confidence: N/A)
    - `vendor_fax`: N/A (confidence: N/A)
    - `vendor_id`: N/A (confidence: N/A)
    - `vendor_website`: N/A (confidence: N/A)

---

### HYD001 5160530790NOV2025.pdf

- **Is Scanned:** ❌ No
- **Extraction Rate:** 30.2%
- **Fields Extracted:** 16/53
- **Line Items:** 19
- **Overall Confidence:** 0.810
- **Multimodal LLM Triggered:** ❌ No
- **Text LLM Triggered:** ✅ Yes
- **Text LLM Success:** ✅
- **False Negatives:** 37

  False negative fields:
    - `business_number`: N/A (confidence: N/A)
    - `contract_id`: N/A (confidence: N/A)
    - `currency`: N/A (confidence: N/A)
    - `customer_email`: N/A (confidence: N/A)
    - `customer_fax`: N/A (confidence: N/A)
    - `customer_phone`: N/A (confidence: N/A)
    - `delivery_date`: N/A (confidence: N/A)
    - `deposit_amount`: N/A (confidence: N/A)
    - `discount_amount`: N/A (confidence: N/A)
    - `entity`: N/A (confidence: N/A)
    - `gst_amount`: N/A (confidence: N/A)
    - `gst_number`: N/A (confidence: N/A)
    - `gst_rate`: N/A (confidence: N/A)
    - `handling_fee`: N/A (confidence: N/A)
    - `hst_amount`: N/A (confidence: N/A)
    - `hst_rate`: N/A (confidence: N/A)
    - `invoice_number`: N/A (confidence: N/A)
    - `invoice_type`: N/A (confidence: N/A)
    - `payment_due_upon`: N/A (confidence: N/A)
    - `payment_method`: N/A (confidence: N/A)
    - `payment_terms`: N/A (confidence: N/A)
    - `po_number`: N/A (confidence: N/A)
    - `pst_amount`: N/A (confidence: N/A)
    - `pst_number`: N/A (confidence: N/A)
    - `pst_rate`: N/A (confidence: N/A)
    - `qst_amount`: N/A (confidence: N/A)
    - `qst_number`: N/A (confidence: N/A)
    - `qst_rate`: N/A (confidence: N/A)
    - `remit_to_name`: N/A (confidence: N/A)
    - `shipping_amount`: N/A (confidence: N/A)
    - `shipping_date`: N/A (confidence: N/A)
    - `standing_offer_number`: N/A (confidence: N/A)
    - `subtotal`: N/A (confidence: N/A)
    - `tax_registration_number`: N/A (confidence: N/A)
    - `vendor_email`: N/A (confidence: N/A)
    - `vendor_fax`: N/A (confidence: N/A)
    - `vendor_id`: N/A (confidence: N/A)

---

### TEL006 4222600.pdf

- **Is Scanned:** ❌ No
- **Extraction Rate:** 41.5%
- **Fields Extracted:** 22/53
- **Line Items:** 360
- **Overall Confidence:** 0.856
- **Multimodal LLM Triggered:** ❌ No
- **Text LLM Triggered:** ✅ Yes
- **Text LLM Success:** ✅
- **False Negatives:** 31

  False negative fields:
    - `business_number`: N/A (confidence: N/A)
    - `contract_id`: N/A (confidence: N/A)
    - `currency`: N/A (confidence: N/A)
    - `customer_email`: N/A (confidence: N/A)
    - `customer_fax`: N/A (confidence: N/A)
    - `customer_phone`: N/A (confidence: N/A)
    - `delivery_date`: N/A (confidence: N/A)
    - `deposit_amount`: N/A (confidence: N/A)
    - `discount_amount`: N/A (confidence: N/A)
    - `entity`: N/A (confidence: N/A)
    - `gst_number`: N/A (confidence: N/A)
    - `gst_rate`: N/A (confidence: N/A)
    - `handling_fee`: N/A (confidence: N/A)
    - `hst_amount`: N/A (confidence: N/A)
    - `hst_rate`: N/A (confidence: N/A)
    - `invoice_type`: N/A (confidence: N/A)
    - `payment_due_upon`: N/A (confidence: N/A)
    - `payment_method`: N/A (confidence: N/A)
    - `payment_terms`: N/A (confidence: N/A)
    - `pst_rate`: N/A (confidence: N/A)
    - `qst_number`: N/A (confidence: N/A)
    - `qst_rate`: N/A (confidence: N/A)
    - `remit_to_name`: N/A (confidence: N/A)
    - `shipping_amount`: N/A (confidence: N/A)
    - `shipping_date`: N/A (confidence: N/A)
    - `standing_offer_number`: N/A (confidence: N/A)
    - `tax_registration_number`: N/A (confidence: N/A)
    - `vendor_email`: N/A (confidence: N/A)
    - `vendor_fax`: N/A (confidence: N/A)
    - `vendor_id`: N/A (confidence: N/A)
    - `vendor_website`: N/A (confidence: N/A)

---

### ENB001 166574659065NOV2025.pdf

- **Is Scanned:** ❌ No
- **Extraction Rate:** 35.8%
- **Fields Extracted:** 19/53
- **Line Items:** 14
- **Overall Confidence:** 0.838
- **Multimodal LLM Triggered:** ❌ No
- **Text LLM Triggered:** ✅ Yes
- **Text LLM Success:** ✅
- **False Negatives:** 34

  False negative fields:
    - `business_number`: N/A (confidence: N/A)
    - `contract_id`: N/A (confidence: N/A)
    - `currency`: N/A (confidence: N/A)
    - `customer_email`: N/A (confidence: N/A)
    - `customer_fax`: N/A (confidence: N/A)
    - `customer_phone`: N/A (confidence: N/A)
    - `delivery_date`: N/A (confidence: N/A)
    - `deposit_amount`: N/A (confidence: N/A)
    - `discount_amount`: N/A (confidence: N/A)
    - `gst_amount`: N/A (confidence: N/A)
    - `gst_number`: N/A (confidence: N/A)
    - `gst_rate`: N/A (confidence: N/A)
    - `handling_fee`: N/A (confidence: N/A)
    - `hst_rate`: N/A (confidence: N/A)
    - `invoice_number`: N/A (confidence: N/A)
    - `invoice_type`: N/A (confidence: N/A)
    - `payment_due_upon`: N/A (confidence: N/A)
    - `payment_method`: N/A (confidence: N/A)
    - `payment_terms`: N/A (confidence: N/A)
    - `po_number`: N/A (confidence: N/A)
    - `pst_amount`: N/A (confidence: N/A)
    - `pst_number`: N/A (confidence: N/A)
    - `pst_rate`: N/A (confidence: N/A)
    - `qst_amount`: N/A (confidence: N/A)
    - `qst_number`: N/A (confidence: N/A)
    - `qst_rate`: N/A (confidence: N/A)
    - `reference_number`: N/A (confidence: N/A)
    - `shipping_amount`: N/A (confidence: N/A)
    - `shipping_date`: N/A (confidence: N/A)
    - `standing_offer_number`: N/A (confidence: N/A)
    - `tax_registration_number`: N/A (confidence: N/A)
    - `vendor_email`: N/A (confidence: N/A)
    - `vendor_fax`: N/A (confidence: N/A)
    - `vendor_id`: N/A (confidence: N/A)

---

## False Negatives Analysis

**Total False Negatives:** 159

### False Negatives by Field Name

| Field Name | Occurrences |
|------------|-------------|
| `contract_id` | 5 |
| `customer_email` | 5 |
| `deposit_amount` | 5 |
| `customer_fax` | 5 |
| `delivery_date` | 5 |
| `customer_phone` | 5 |
| `discount_amount` | 5 |
| `payment_due_upon` | 5 |
| `handling_fee` | 5 |
| `hst_rate` | 5 |
| `shipping_date` | 5 |
| `tax_registration_number` | 5 |
| `vendor_id` | 5 |
| `invoice_type` | 5 |
| `payment_method` | 5 |
| `shipping_amount` | 5 |
| `qst_rate` | 5 |
| `qst_number` | 5 |
| `standing_offer_number` | 4 |
| `currency` | 4 |
| `business_number` | 4 |
| `qst_amount` | 4 |
| `pst_rate` | 4 |
| `hst_amount` | 4 |
| `vendor_email` | 4 |
| `vendor_fax` | 4 |
| `reference_number` | 3 |
| `gst_number` | 3 |
| `entity` | 3 |
| `pst_number` | 3 |
| `vendor_website` | 3 |
| `gst_rate` | 3 |
| `payment_terms` | 3 |
| `pst_amount` | 3 |
| `remit_to_name` | 2 |
| `gst_amount` | 2 |
| `period_end` | 2 |
| `invoice_number` | 2 |
| `po_number` | 2 |
| `customer_id` | 1 |
| `period_start` | 1 |
| `subtotal` | 1 |

### False Negatives by PDF

| PDF Name | False Negatives |
|----------|----------------|
| `HYD001 5160530790NOV2025.pdf` | 37 |
| `ENB001 166574659065NOV2025.pdf` | 34 |
| `TEL006 4222600.pdf` | 31 |
| `ANA005 90443097.pdf` | 29 |
| `ACC012 4202092525.pdf` | 28 |

## Line Items Summary

Line items are extracted and structured for the new `line_items` table format.

### Line Items Structure

Each line item includes:
- `line_number`: Sequential line number
- `description`: Item description
- `quantity`: Quantity (if available)
- `unit_price`: Unit price (if available)
- `amount`: Line item total amount
- `tax_amount`: Tax amount for this line
- `gst_amount`: GST amount (if applicable)
- `pst_amount`: PST amount (if applicable)
- `qst_amount`: QST amount (if applicable)
- `confidence`: Extraction confidence score

**Total Line Items Extracted:** 399

## Process Steps Log

| Step | Description | Status | Timestamp |
|------|-------------|--------|-----------|
| INITIALIZATION | Initializing Multimodal LLM extractor | ℹ️ INFO | 2026-01-08T19:54:10.788776 |
| TEST_START | Starting test for ACC012 4202092525.pdf | ℹ️ INFO | 2026-01-08T19:54:10.788776 |
| EXTRACTION | Running Multimodal LLM extraction for ACC012 4202092525.pdf | ℹ️ INFO | 2026-01-08T19:54:10.788776 |
| EXTRACTION | Multimodal LLM extraction completed for ACC012 4202092525.pdf | ✅ SUCCESS | 2026-01-08T19:54:25.206452 |
| TEST_START | Starting test for ANA005 90443097.pdf | ℹ️ INFO | 2026-01-08T19:54:25.206452 |
| EXTRACTION | Running Multimodal LLM extraction for ANA005 90443097.pdf | ℹ️ INFO | 2026-01-08T19:54:25.206452 |
| EXTRACTION | Multimodal LLM extraction completed for ANA005 90443097.pdf | ✅ SUCCESS | 2026-01-08T19:54:37.835447 |
| TEST_START | Starting test for HYD001 5160530790NOV2025.pdf | ℹ️ INFO | 2026-01-08T19:54:37.835946 |
| EXTRACTION | Running Multimodal LLM extraction for HYD001 5160530790NOV2025.pdf | ℹ️ INFO | 2026-01-08T19:54:37.835946 |
| EXTRACTION | Multimodal LLM extraction completed for HYD001 5160530790NOV2025.pdf | ✅ SUCCESS | 2026-01-08T19:55:03.417063 |
| TEST_START | Starting test for TEL006 4222600.pdf | ℹ️ INFO | 2026-01-08T19:55:03.417063 |
| EXTRACTION | Running Multimodal LLM extraction for TEL006 4222600.pdf | ℹ️ INFO | 2026-01-08T19:55:03.417063 |
| EXTRACTION | Multimodal LLM extraction completed for TEL006 4222600.pdf | ✅ SUCCESS | 2026-01-08T19:55:31.751867 |
| TEST_START | Starting test for ENB001 166574659065NOV2025.pdf | ℹ️ INFO | 2026-01-08T19:55:31.751867 |
| EXTRACTION | Running Multimodal LLM extraction for ENB001 166574659065NOV2025.pdf | ℹ️ INFO | 2026-01-08T19:55:31.751867 |
| EXTRACTION | Multimodal LLM extraction completed for ENB001 166574659065NOV2025.pdf | ✅ SUCCESS | 2026-01-08T19:55:46.299687 |

---

## Confusion Matrix Analysis

Detailed confusion matrix analysis has been generated. See:
- `confusion_matrix_per_pdf.csv` - Per-PDF confusion matrices
- `confusion_matrix_per_field.csv` - Per-field confusion matrices
- `confusion_matrix_overall.csv` - Overall confusion matrix
- `confusion_matrix_report.md` - Comprehensive confusion matrix report

### Key Metrics

**Confusion Matrix Categories:**
- **True Positive (TP):** Field correctly extracted with confidence
- **False Positive (FP):** Field extracted but with low/no confidence
- **False Negative (FN):** Field should be extracted (has confidence/DI source) but isn't
- **True Negative (TN):** Field correctly not extracted (no value, no confidence)

**Performance Metrics:**
- **Precision:** TP / (TP + FP) - Of all extracted fields, how many are correct?
- **Recall:** TP / (TP + FN) - Of all extractable fields, how many were found?
- **F1 Score:** Harmonic mean of precision and recall
- **Accuracy:** (TP + TN) / Total - Overall correctness

---

**Report End**