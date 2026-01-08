# Base LLM Extraction Test Report with False Negative Detection

**Generated:** 2026-01-08 19:53:15 UTC
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

### 3. Field Extraction
- **Step:** Map DI fields to canonical schema
- **Description:** Extract fields from DI result using FieldExtractor
- **Status:** ✅ Executed in test
- **Output:** Invoice object with canonical fields populated
- **Includes:** Higher-level invoice fields AND line items (new table structure)

### 4. Confidence Calculation
- **Step:** Calculate field-level and overall confidence
- **Description:** Analyze confidence scores from DI, categorize as high/medium/low
- **Status:** ✅ Executed in test
- **Output:** Confidence scores and categories for each field

### 5. Low-Confidence Field Identification
- **Step:** Identify fields requiring LLM enhancement
- **Description:** Find fields with confidence < threshold or missing values
- **Status:** ✅ Executed in test
- **Output:** List of low-confidence fields for LLM processing

### 6. Base LLM Fallback
- **Step:** Text-based LLM extraction
- **Description:** Use Azure OpenAI to extract/improve low-confidence fields from DI text
- **Status:** ✅ Executed in test (real Azure OpenAI API)
- **Output:** Enhanced field values with improved confidence

### 7. Line Items Processing
- **Step:** Extract and structure line items
- **Description:** Process line items from DI, structure for new table format
- **Status:** ✅ Executed in test
- **Output:** Line items array ready for line_items table
- **Structure:** Includes line_number, description, quantity, unit_price, amount, taxes, etc.

### 8. Extraction Detection
- **Step:** Determine if fields are extracted
- **Description:** Check if field has non-empty value based on type
- **Status:** ✅ Executed in test
- **Output:** Boolean flag for each field indicating extraction status

### 9. False Negative Detection
- **Step:** Identify potential false negatives
- **Description:** Find fields marked as not extracted but have values
- **Status:** ✅ Executed in test
- **Output:** List of potential false negatives with analysis

### Steps NOT Executed in This Test
- ❌ **Multimodal LLM:** Not executed (Base LLM only test)
- ❌ **Database Persistence:** Not executed (standalone test)
- ❌ **Validation:** Not executed (standalone test)
- ❌ **HITL Review:** Not executed (standalone test)

---

## Executive Summary

- **Total PDFs Tested:** 5
- **Total Fields Available:** 265
- **Total Fields Extracted:** 110
- **Overall Extraction Rate:** 41.5%
- **Total Line Items Extracted:** 399
- **False Negatives Detected:** 155

---

## Results by PDF

### ACC012 4202092525.pdf

- **Extraction Rate:** 50.9%
- **Fields Extracted:** 27/53
- **DI Extracted:** 26
- **LLM Extracted:** 14
- **LLM Only:** 14
- **Line Items:** 1
- **Overall Confidence:** 0.895
- **LLM Triggered:** ✅ Yes
- **LLM Success:** ✅
- **LLM Groups Processed:** 3
- **LLM Groups Succeeded:** 3
- **LLM Improved Fields:** 14
- **False Negatives:** 26

  False negative fields:
    - `business_number`: N/A (confidence: N/A)
    - `contract_id`: N/A (confidence: N/A)
    - `customer_email`: N/A (confidence: N/A)
    - `customer_fax`: N/A (confidence: N/A)
    - `customer_id`: N/A (confidence: N/A)
    - `customer_phone`: N/A (confidence: N/A)
    - `delivery_date`: N/A (confidence: N/A)
    - `deposit_amount`: N/A (confidence: N/A)
    - `discount_amount`: N/A (confidence: N/A)
    - `entity`: N/A (confidence: N/A)
    - `handling_fee`: N/A (confidence: N/A)
    - `hst_amount`: N/A (confidence: N/A)
    - `hst_rate`: N/A (confidence: N/A)
    - `invoice_type`: N/A (confidence: N/A)
    - `payment_due_upon`: N/A (confidence: N/A)
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

- **Extraction Rate:** 43.4%
- **Fields Extracted:** 23/53
- **DI Extracted:** 22
- **LLM Extracted:** 9
- **LLM Only:** 9
- **Line Items:** 5
- **Overall Confidence:** 0.891
- **LLM Triggered:** ✅ Yes
- **LLM Success:** ✅
- **LLM Groups Processed:** 2
- **LLM Groups Succeeded:** 2
- **LLM Improved Fields:** 9
- **False Negatives:** 30

  False negative fields:
    - `business_number`: N/A (confidence: N/A)
    - `contract_id`: N/A (confidence: N/A)
    - `customer_email`: N/A (confidence: N/A)
    - `customer_fax`: N/A (confidence: N/A)
    - `customer_phone`: N/A (confidence: N/A)
    - `delivery_date`: N/A (confidence: N/A)
    - `deposit_amount`: N/A (confidence: N/A)
    - `discount_amount`: N/A (confidence: N/A)
    - `entity`: N/A (confidence: N/A)
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
    - `shipping_amount`: N/A (confidence: N/A)
    - `shipping_date`: N/A (confidence: N/A)
    - `tax_registration_number`: N/A (confidence: N/A)
    - `vendor_email`: N/A (confidence: N/A)
    - `vendor_fax`: N/A (confidence: N/A)
    - `vendor_id`: N/A (confidence: N/A)
    - `vendor_website`: N/A (confidence: N/A)

---

### HYD001 5160530790NOV2025.pdf

- **Extraction Rate:** 32.1%
- **Fields Extracted:** 17/53
- **DI Extracted:** 17
- **LLM Extracted:** 10
- **LLM Only:** 10
- **Line Items:** 19
- **Overall Confidence:** 0.837
- **LLM Triggered:** ✅ Yes
- **LLM Success:** ✅
- **LLM Groups Processed:** 3
- **LLM Groups Succeeded:** 3
- **LLM Improved Fields:** 10
- **False Negatives:** 36

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
    - `invoice_type`: N/A (confidence: N/A)
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

- **Extraction Rate:** 41.5%
- **Fields Extracted:** 22/53
- **DI Extracted:** 22
- **LLM Extracted:** 12
- **LLM Only:** 12
- **Line Items:** 360
- **Overall Confidence:** 0.850
- **LLM Triggered:** ✅ Yes
- **LLM Success:** ✅
- **LLM Groups Processed:** 3
- **LLM Groups Succeeded:** 3
- **LLM Improved Fields:** 12
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

- **Extraction Rate:** 39.6%
- **Fields Extracted:** 21/53
- **DI Extracted:** 20
- **LLM Extracted:** 10
- **LLM Only:** 10
- **Line Items:** 14
- **Overall Confidence:** 0.865
- **LLM Triggered:** ✅ Yes
- **LLM Success:** ✅
- **LLM Groups Processed:** 3
- **LLM Groups Succeeded:** 3
- **LLM Improved Fields:** 10
- **False Negatives:** 32

  False negative fields:
    - `business_number`: N/A (confidence: N/A)
    - `contract_id`: N/A (confidence: N/A)
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
    - `hst_rate`: N/A (confidence: N/A)
    - `invoice_type`: N/A (confidence: N/A)
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

**Total False Negatives:** 155

### False Negatives by Field Name

| Field Name | Occurrences |
|------------|-------------|
| `business_number` | 5 |
| `contract_id` | 5 |
| `customer_email` | 5 |
| `customer_fax` | 5 |
| `customer_phone` | 5 |
| `deposit_amount` | 5 |
| `delivery_date` | 5 |
| `entity` | 5 |
| `discount_amount` | 5 |
| `shipping_date` | 5 |
| `tax_registration_number` | 5 |
| `hst_rate` | 5 |
| `handling_fee` | 5 |
| `invoice_type` | 5 |
| `shipping_amount` | 5 |
| `qst_rate` | 5 |
| `qst_number` | 5 |
| `vendor_id` | 5 |
| `vendor_email` | 4 |
| `standing_offer_number` | 4 |
| `qst_amount` | 4 |
| `pst_rate` | 4 |
| `hst_amount` | 4 |
| `payment_method` | 4 |
| `vendor_fax` | 4 |
| `vendor_website` | 3 |
| `reference_number` | 3 |
| `gst_number` | 3 |
| `pst_number` | 3 |
| `payment_terms` | 3 |
| `payment_due_upon` | 3 |
| `gst_rate` | 3 |
| `pst_amount` | 3 |
| `remit_to_name` | 2 |
| `currency` | 2 |
| `period_end` | 2 |
| `gst_amount` | 2 |
| `po_number` | 2 |
| `customer_id` | 1 |
| `period_start` | 1 |
| `subtotal` | 1 |

### False Negatives by PDF

| PDF Name | False Negatives |
|----------|----------------|
| `HYD001 5160530790NOV2025.pdf` | 36 |
| `ENB001 166574659065NOV2025.pdf` | 32 |
| `TEL006 4222600.pdf` | 31 |
| `ANA005 90443097.pdf` | 30 |
| `ACC012 4202092525.pdf` | 26 |

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
| INITIALIZATION | Initializing Base LLM extractor | ℹ️ INFO | 2026-01-08T19:51:39.964435 |
| TEST_START | Starting test for ACC012 4202092525.pdf | ℹ️ INFO | 2026-01-08T19:51:39.964435 |
| EXTRACTION | Running Base LLM extraction for ACC012 4202092525.pdf | ℹ️ INFO | 2026-01-08T19:51:39.964435 |
| EXTRACTION | Base LLM extraction completed for ACC012 4202092525.pdf | ✅ SUCCESS | 2026-01-08T19:51:53.326458 |
| TEST_START | Starting test for ANA005 90443097.pdf | ℹ️ INFO | 2026-01-08T19:51:53.326458 |
| EXTRACTION | Running Base LLM extraction for ANA005 90443097.pdf | ℹ️ INFO | 2026-01-08T19:51:53.326458 |
| EXTRACTION | Base LLM extraction completed for ANA005 90443097.pdf | ✅ SUCCESS | 2026-01-08T19:52:04.454128 |
| TEST_START | Starting test for HYD001 5160530790NOV2025.pdf | ℹ️ INFO | 2026-01-08T19:52:04.454128 |
| EXTRACTION | Running Base LLM extraction for HYD001 5160530790NOV2025.pdf | ℹ️ INFO | 2026-01-08T19:52:04.454128 |
| EXTRACTION | Base LLM extraction completed for HYD001 5160530790NOV2025.pdf | ✅ SUCCESS | 2026-01-08T19:52:32.352851 |
| TEST_START | Starting test for TEL006 4222600.pdf | ℹ️ INFO | 2026-01-08T19:52:32.352851 |
| EXTRACTION | Running Base LLM extraction for TEL006 4222600.pdf | ℹ️ INFO | 2026-01-08T19:52:32.352851 |
| EXTRACTION | Base LLM extraction completed for TEL006 4222600.pdf | ✅ SUCCESS | 2026-01-08T19:53:00.345678 |
| TEST_START | Starting test for ENB001 166574659065NOV2025.pdf | ℹ️ INFO | 2026-01-08T19:53:00.345678 |
| EXTRACTION | Running Base LLM extraction for ENB001 166574659065NOV2025.pdf | ℹ️ INFO | 2026-01-08T19:53:00.345678 |
| EXTRACTION | Base LLM extraction completed for ENB001 166574659065NOV2025.pdf | ✅ SUCCESS | 2026-01-08T19:53:15.174095 |

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