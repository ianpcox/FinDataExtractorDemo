# DI OCR Extraction Test Report with False Negative Detection

**Generated:** 2026-01-08 16:43:03 UTC
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
- **Total Fields Extracted:** 55
- **Overall Extraction Rate:** 20.8%
- **False Negatives Detected:** 15

---

## Results by PDF

### ACC012 4202092525.pdf

- **Extraction Rate:** 22.6%
- **Fields Extracted:** 12/53
- **High Confidence (>=0.75):** 10
- **Medium Confidence (0.50-0.75):** 0
- **Low Confidence (<0.50):** 0
- **Overall Confidence:** 0.945
- **DI Duration:** 5.63 seconds
- **False Negatives:** 1

  False negative fields:
    - `entity`: N/A (confidence: N/A)

---

### ANA005 90443097.pdf

- **Extraction Rate:** 20.8%
- **Fields Extracted:** 11/53
- **High Confidence (>=0.75):** 10
- **Medium Confidence (0.50-0.75):** 0
- **Low Confidence (<0.50):** 0
- **Overall Confidence:** 0.932
- **DI Duration:** 5.50 seconds
- **False Negatives:** 3

  False negative fields:
    - `entity`: N/A (confidence: N/A)
    - `remit_to_address`: N/A (confidence: N/A)
    - `vendor_address`: N/A (confidence: N/A)

---

### HYD001 5160530790NOV2025.pdf

- **Extraction Rate:** 15.1%
- **Fields Extracted:** 8/53
- **High Confidence (>=0.75):** 6
- **Medium Confidence (0.50-0.75):** 0
- **Low Confidence (<0.50):** 1
- **Overall Confidence:** 0.847
- **DI Duration:** 18.78 seconds
- **False Negatives:** 5

  False negative fields:
    - `bill_to_address`: N/A (confidence: N/A)
    - `entity`: N/A (confidence: N/A)
    - `remit_to_address`: N/A (confidence: N/A)
    - `subtotal`: N/A (confidence: N/A)
    - `vendor_address`: N/A (confidence: N/A)

---

### TEL006 4222600.pdf

- **Extraction Rate:** 24.5%
- **Fields Extracted:** 13/53
- **High Confidence (>=0.75):** 8
- **Medium Confidence (0.50-0.75):** 2
- **Low Confidence (<0.50):** 0
- **Overall Confidence:** 0.884
- **DI Duration:** 20.53 seconds
- **False Negatives:** 3

  False negative fields:
    - `bill_to_address`: N/A (confidence: N/A)
    - `entity`: N/A (confidence: N/A)
    - `remit_to_address`: N/A (confidence: N/A)

---

### ENB001 166574659065NOV2025.pdf

- **Extraction Rate:** 20.8%
- **Fields Extracted:** 11/53
- **High Confidence (>=0.75):** 8
- **Medium Confidence (0.50-0.75):** 0
- **Low Confidence (<0.50):** 0
- **Overall Confidence:** 0.910
- **DI Duration:** 9.51 seconds
- **False Negatives:** 3

  False negative fields:
    - `bill_to_address`: N/A (confidence: N/A)
    - `entity`: N/A (confidence: N/A)
    - `remit_to_address`: N/A (confidence: N/A)

---

## False Negatives Analysis

**Total False Negatives:** 15

### False Negatives by Field Name

| Field Name | Occurrences |
|------------|-------------|
| `entity` | 5 |
| `remit_to_address` | 4 |
| `bill_to_address` | 3 |
| `vendor_address` | 2 |
| `subtotal` | 1 |

### False Negatives by PDF

| PDF Name | False Negatives |
|----------|----------------|
| `HYD001 5160530790NOV2025.pdf` | 5 |
| `ANA005 90443097.pdf` | 3 |
| `ENB001 166574659065NOV2025.pdf` | 3 |
| `TEL006 4222600.pdf` | 3 |
| `ACC012 4202092525.pdf` | 1 |

---

## Process Steps Log

| Step | Description | Status | Timestamp |
|------|-------------|--------|-----------|
| INITIALIZATION | Initializing DI OCR extractor | ℹ️ INFO | 2026-01-08T16:42:03.063827 |
| TEST_START | Starting test for ACC012 4202092525.pdf | ℹ️ INFO | 2026-01-08T16:42:03.063827 |
| EXTRACTION | Running DI OCR extraction for ACC012 4202092525.pdf | ℹ️ INFO | 2026-01-08T16:42:03.063827 |
| EXTRACTION | DI OCR extraction completed for ACC012 4202092525.pdf | ✅ SUCCESS | 2026-01-08T16:42:08.702005 |
| TEST_START | Starting test for ANA005 90443097.pdf | ℹ️ INFO | 2026-01-08T16:42:08.702005 |
| EXTRACTION | Running DI OCR extraction for ANA005 90443097.pdf | ℹ️ INFO | 2026-01-08T16:42:08.702005 |
| EXTRACTION | DI OCR extraction completed for ANA005 90443097.pdf | ✅ SUCCESS | 2026-01-08T16:42:14.201450 |
| TEST_START | Starting test for HYD001 5160530790NOV2025.pdf | ℹ️ INFO | 2026-01-08T16:42:14.201450 |
| EXTRACTION | Running DI OCR extraction for HYD001 5160530790NOV2025.pdf | ℹ️ INFO | 2026-01-08T16:42:14.201450 |
| EXTRACTION | DI OCR extraction completed for HYD001 5160530790NOV2025.pdf | ✅ SUCCESS | 2026-01-08T16:42:32.999747 |
| TEST_START | Starting test for TEL006 4222600.pdf | ℹ️ INFO | 2026-01-08T16:42:32.999747 |
| EXTRACTION | Running DI OCR extraction for TEL006 4222600.pdf | ℹ️ INFO | 2026-01-08T16:42:32.999747 |
| EXTRACTION | DI OCR extraction completed for TEL006 4222600.pdf | ✅ SUCCESS | 2026-01-08T16:42:53.640907 |
| TEST_START | Starting test for ENB001 166574659065NOV2025.pdf | ℹ️ INFO | 2026-01-08T16:42:53.640907 |
| EXTRACTION | Running DI OCR extraction for ENB001 166574659065NOV2025.pdf | ℹ️ INFO | 2026-01-08T16:42:53.640907 |
| EXTRACTION | DI OCR extraction completed for ENB001 166574659065NOV2025.pdf | ✅ SUCCESS | 2026-01-08T16:43:03.152348 |

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