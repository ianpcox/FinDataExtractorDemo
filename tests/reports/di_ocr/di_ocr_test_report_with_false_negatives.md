# DI OCR Extraction Test Report with False Negative Detection

**Generated:** 2026-01-08 19:50:15 UTC
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

### 5. Extraction Detection
- **Step:** Determine if fields are extracted
- **Description:** Check if field has non-empty value based on type
- **Status:** ✅ Executed in test
- **Output:** Boolean flag for each field indicating extraction status

### 6. False Negative Detection
- **Step:** Identify potential false negatives
- **Description:** Find fields marked as not extracted but have values
- **Status:** ✅ Executed in test
- **Output:** List of potential false negatives with analysis

### Steps NOT Executed in This Test
- ❌ **LLM Fallback:** Not executed (DI OCR only test)
- ❌ **Multimodal LLM:** Not executed (DI OCR only test)
- ❌ **Database Persistence:** Not executed (standalone test)
- ❌ **Validation:** Not executed (standalone test)
- ❌ **HITL Review:** Not executed (standalone test)

---

## Executive Summary

- **Total PDFs Tested:** 5
- **Total Fields Available:** 265
- **Total Fields Extracted:** 72
- **Overall Extraction Rate:** 27.2%
- **False Negatives Detected:** 6

---

## Results by PDF

### ACC012 4202092525.pdf

- **Extraction Rate:** 28.3%
- **Fields Extracted:** 15/53
- **High Confidence (>=0.75):** 12
- **Medium Confidence (0.50-0.75):** 0
- **Low Confidence (<0.50):** 0
- **Line Items:** 1
- **Overall Confidence:** 0.937
- **DI Duration:** 5.88 seconds
- **False Negatives:** 1

  False negative fields:
    - `entity`: N/A (confidence: N/A)

---

### ANA005 90443097.pdf

- **Extraction Rate:** 28.3%
- **Fields Extracted:** 15/53
- **High Confidence (>=0.75):** 13
- **Medium Confidence (0.50-0.75):** 0
- **Low Confidence (<0.50):** 0
- **Line Items:** 5
- **Overall Confidence:** 0.929
- **DI Duration:** 5.45 seconds
- **False Negatives:** 1

  False negative fields:
    - `entity`: N/A (confidence: N/A)

---

### HYD001 5160530790NOV2025.pdf

- **Extraction Rate:** 22.6%
- **Fields Extracted:** 12/53
- **High Confidence (>=0.75):** 7
- **Medium Confidence (0.50-0.75):** 2
- **Low Confidence (<0.50):** 1
- **Line Items:** 19
- **Overall Confidence:** 0.820
- **DI Duration:** 20.59 seconds
- **False Negatives:** 2

  False negative fields:
    - `entity`: N/A (confidence: N/A)
    - `subtotal`: N/A (confidence: N/A)

---

### TEL006 4222600.pdf

- **Extraction Rate:** 30.2%
- **Fields Extracted:** 16/53
- **High Confidence (>=0.75):** 10
- **Medium Confidence (0.50-0.75):** 2
- **Low Confidence (<0.50):** 0
- **Line Items:** 360
- **Overall Confidence:** 0.880
- **DI Duration:** 20.52 seconds
- **False Negatives:** 1

  False negative fields:
    - `entity`: N/A (confidence: N/A)

---

### ENB001 166574659065NOV2025.pdf

- **Extraction Rate:** 26.4%
- **Fields Extracted:** 14/53
- **High Confidence (>=0.75):** 10
- **Medium Confidence (0.50-0.75):** 0
- **Low Confidence (<0.50):** 0
- **Line Items:** 14
- **Overall Confidence:** 0.906
- **DI Duration:** 7.44 seconds
- **False Negatives:** 1

  False negative fields:
    - `entity`: N/A (confidence: N/A)

---

## False Negatives Analysis

**Total False Negatives:** 6

### False Negatives by Field Name

| Field Name | Occurrences |
|------------|-------------|
| `entity` | 5 |
| `subtotal` | 1 |

### False Negatives by PDF

| PDF Name | False Negatives |
|----------|----------------|
| `HYD001 5160530790NOV2025.pdf` | 2 |
| `ACC012 4202092525.pdf` | 1 |
| `ANA005 90443097.pdf` | 1 |
| `ENB001 166574659065NOV2025.pdf` | 1 |
| `TEL006 4222600.pdf` | 1 |

---

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
| INITIALIZATION | Initializing DI OCR extractor | ℹ️ INFO | 2026-01-08T19:49:14.995081 |
| TEST_START | Starting test for ACC012 4202092525.pdf | ℹ️ INFO | 2026-01-08T19:49:14.995081 |
| EXTRACTION | Running DI OCR extraction for ACC012 4202092525.pdf | ℹ️ INFO | 2026-01-08T19:49:14.995081 |
| EXTRACTION | DI OCR extraction completed for ACC012 4202092525.pdf | ✅ SUCCESS | 2026-01-08T19:49:20.883626 |
| TEST_START | Starting test for ANA005 90443097.pdf | ℹ️ INFO | 2026-01-08T19:49:20.883626 |
| EXTRACTION | Running DI OCR extraction for ANA005 90443097.pdf | ℹ️ INFO | 2026-01-08T19:49:20.883626 |
| EXTRACTION | DI OCR extraction completed for ANA005 90443097.pdf | ✅ SUCCESS | 2026-01-08T19:49:26.336789 |
| TEST_START | Starting test for HYD001 5160530790NOV2025.pdf | ℹ️ INFO | 2026-01-08T19:49:26.336789 |
| EXTRACTION | Running DI OCR extraction for HYD001 5160530790NOV2025.pdf | ℹ️ INFO | 2026-01-08T19:49:26.336789 |
| EXTRACTION | DI OCR extraction completed for HYD001 5160530790NOV2025.pdf | ✅ SUCCESS | 2026-01-08T19:49:46.951438 |
| TEST_START | Starting test for TEL006 4222600.pdf | ℹ️ INFO | 2026-01-08T19:49:46.951938 |
| EXTRACTION | Running DI OCR extraction for TEL006 4222600.pdf | ℹ️ INFO | 2026-01-08T19:49:46.951938 |
| EXTRACTION | DI OCR extraction completed for TEL006 4222600.pdf | ✅ SUCCESS | 2026-01-08T19:50:07.589819 |
| TEST_START | Starting test for ENB001 166574659065NOV2025.pdf | ℹ️ INFO | 2026-01-08T19:50:07.589819 |
| EXTRACTION | Running DI OCR extraction for ENB001 166574659065NOV2025.pdf | ℹ️ INFO | 2026-01-08T19:50:07.589819 |
| EXTRACTION | DI OCR extraction completed for ENB001 166574659065NOV2025.pdf | ✅ SUCCESS | 2026-01-08T19:50:15.039616 |

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