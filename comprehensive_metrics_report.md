# Comprehensive Extraction Metrics Report

This report provides comprehensive per-field and document-level evaluation metrics for invoice extraction.

## Summary

**Total Canonical Fields:** 53 (from canonical field coverage reports)
**Fields Evaluated:** 53
**Total Documents:** 5

### Document-Level Summary

- **Mean Extraction Rate:** 20.8% (fields extracted / 53 canonical fields)
- **Median Extraction Rate:** 20.8%
- **Mean Document Accuracy:** 0.000
- **Mean Document F1 Score:** 0.000
- **Hard Pass Rate (All Required Fields Correct):** 0.0% (0/5 documents)
- **Mean Overall Confidence:** 0.906
- **Mean Business Impact Score:** 0.837
- **Mean Weighted F1:** 0.891

### Confidence Calibration

- **Expected Calibration Error (ECE):** 0.323 (lower is better, 0.0 = perfectly calibrated)
- **Max Calibration Error (MCE):** 0.351
- **Calibration Slope:** 0.000 (correlation between confidence and correctness)

#### Confidence Calibration by Bin

| Confidence Bin | Mean Confidence | Mean Correctness | Samples | Calibration Gap |
|----------------|-----------------|------------------|---------|-----------------|
| 0.7-0.8 | 0.719 | 1.000 | 2 | 0.281 |
| 0.5-0.7 | 0.649 | 1.000 | 3 | 0.351 |

**Interpretation:**
- **Well-calibrated:** Mean correctness ≈ Mean confidence (gap < 0.1)
- **Overconfident:** Mean correctness < Mean confidence (gap > 0.1, correctness lower)
- **Underconfident:** Mean correctness > Mean confidence (gap > 0.1, correctness higher)

## Document-Level Metrics

| PDF Name | Extraction Rate | Accuracy | F1 Score | All Required Fields | Avg Confidence | Business Impact |
|----------|----------------|----------|----------|---------------------|----------------|-----------------|
| ACC012 4202092525.pdf | 22.6% | 0.000 | 0.000 | ✗ (0/0) | 0.946 | 0.817 |
| ANA005 90443097.pdf | 20.8% | 0.000 | 0.000 | ✗ (0/0) | 0.923 | 0.831 |
| ENB001 166574659065NOV2025.pdf | 20.8% | 0.000 | 0.000 | ✗ (0/0) | 0.910 | 0.848 |
| HYD001 5160530790NOV2025.pdf | 15.1% | 0.000 | 0.000 | ✗ (0/0) | 0.859 | 0.876 |
| TEL006 4222600.pdf | 24.5% | 0.000 | 0.000 | ✗ (0/0) | 0.890 | 0.814 |

## Per-Field Metrics

### Metrics Per Field

| Field Name | Precision | Recall | F1 Score | Accuracy | Exact Match | Tolerant Match | Mean Similarity |
|------------|-----------|--------|----------|----------|-------------|----------------|-----------------|
| currency | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| customer_id | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 0.800 | 0.000 |
| customer_name | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| due_date | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 0.800 | 0.000 |
| invoice_date | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| invoice_number | 1.000 | 1.000 | 1.000 | 1.000 | 0.600 | 0.600 | 1.000 |
| payment_terms | 1.000 | 1.000 | 1.000 | 1.000 | 0.400 | 0.400 | 0.000 |
| period_end | 1.000 | 1.000 | 1.000 | 1.000 | 0.400 | 0.400 | 0.000 |
| period_start | 1.000 | 1.000 | 1.000 | 1.000 | 0.600 | 0.600 | 0.000 |
| po_number | 1.000 | 1.000 | 1.000 | 1.000 | 0.600 | 0.600 | 1.000 |
| subtotal | 1.000 | 1.000 | 1.000 | 1.000 | 0.800 | 0.800 | 0.000 |
| tax_amount | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| total_amount | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| vendor_name | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| bill_to_address | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| business_number | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| contract_id | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| customer_email | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| customer_fax | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| customer_phone | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| delivery_date | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| deposit_amount | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| discount_amount | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| entity | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| gst_amount | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| gst_number | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| gst_rate | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| handling_fee | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| hst_amount | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| hst_rate | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| invoice_type | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| payment_due_upon | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| payment_method | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| pst_amount | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| pst_number | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| pst_rate | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| qst_amount | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| qst_number | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| qst_rate | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| reference_number | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| remit_to_address | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| remit_to_name | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| shipping_amount | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| shipping_date | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| standing_offer_number | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| tax_breakdown | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| tax_registration_number | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| vendor_address | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| vendor_email | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| vendor_fax | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| vendor_id | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| vendor_phone | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| vendor_website | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 |

## Detailed Metrics

### currency

- **True Positives:** 5
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 0
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 1.000
- **Tolerant Match Accuracy:** 1.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### customer_id

- **True Positives:** 4
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 1
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.800
- **Tolerant Match Accuracy:** 0.800
- **Mean Similarity:** 0.000
- **Total Documents:** 5

#### Confidence Calibration

| Confidence Bin | Samples | Mean Correctness |
|----------------|---------|------------------|
| 0.9-1.0 | 2 | 1.000 |
| 0.8-0.9 | 2 | 1.000 |

### customer_name

- **True Positives:** 5
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 0
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 1.000
- **Tolerant Match Accuracy:** 1.000
- **Mean Similarity:** 1.000
- **Total Documents:** 5

#### Confidence Calibration

| Confidence Bin | Samples | Mean Correctness |
|----------------|---------|------------------|
| 0.9-1.0 | 3 | 1.000 |
| 0.8-0.9 | 2 | 1.000 |

### due_date

- **True Positives:** 4
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 1
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.800
- **Tolerant Match Accuracy:** 0.800
- **Mean Similarity:** 0.000
- **Total Documents:** 5

#### Confidence Calibration

| Confidence Bin | Samples | Mean Correctness |
|----------------|---------|------------------|
| 0.9-1.0 | 4 | 1.000 |

### invoice_date

- **True Positives:** 5
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 0
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 1.000
- **Tolerant Match Accuracy:** 1.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

#### Confidence Calibration

| Confidence Bin | Samples | Mean Correctness |
|----------------|---------|------------------|
| 0.9-1.0 | 5 | 1.000 |

### invoice_number

- **True Positives:** 3
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 2
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.600
- **Tolerant Match Accuracy:** 0.600
- **Mean Similarity:** 1.000
- **Total Documents:** 5

#### Confidence Calibration

| Confidence Bin | Samples | Mean Correctness |
|----------------|---------|------------------|
| 0.9-1.0 | 3 | 1.000 |

### payment_terms

- **True Positives:** 2
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 3
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.400
- **Tolerant Match Accuracy:** 0.400
- **Mean Similarity:** 0.000
- **Total Documents:** 5

#### Confidence Calibration

| Confidence Bin | Samples | Mean Correctness |
|----------------|---------|------------------|
| 0.9-1.0 | 1 | 1.000 |
| 0.8-0.9 | 1 | 1.000 |

### period_end

- **True Positives:** 2
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 3
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.400
- **Tolerant Match Accuracy:** 0.400
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### period_start

- **True Positives:** 3
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 2
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.600
- **Tolerant Match Accuracy:** 0.600
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### po_number

- **True Positives:** 3
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 2
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.600
- **Tolerant Match Accuracy:** 0.600
- **Mean Similarity:** 1.000
- **Total Documents:** 5

#### Confidence Calibration

| Confidence Bin | Samples | Mean Correctness |
|----------------|---------|------------------|
| 0.9-1.0 | 3 | 1.000 |

### subtotal

- **True Positives:** 4
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 1
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.800
- **Tolerant Match Accuracy:** 0.800
- **Mean Similarity:** 0.000
- **Total Documents:** 5

#### Confidence Calibration

| Confidence Bin | Samples | Mean Correctness |
|----------------|---------|------------------|
| 0.9-1.0 | 2 | 1.000 |
| 0.8-0.9 | 1 | 1.000 |
| 0.5-0.7 | 1 | 1.000 |

### tax_amount

- **True Positives:** 5
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 0
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 1.000
- **Tolerant Match Accuracy:** 1.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

#### Confidence Calibration

| Confidence Bin | Samples | Mean Correctness |
|----------------|---------|------------------|
| 0.9-1.0 | 4 | 1.000 |
| 0.0-0.5 | 1 | 1.000 |

### total_amount

- **True Positives:** 5
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 0
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 1.000
- **Tolerant Match Accuracy:** 1.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

#### Confidence Calibration

| Confidence Bin | Samples | Mean Correctness |
|----------------|---------|------------------|
| 0.9-1.0 | 5 | 1.000 |

### vendor_name

- **True Positives:** 5
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 0
- **Precision:** 1.000
- **Recall:** 1.000
- **F1 Score:** 1.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 1.000
- **Tolerant Match Accuracy:** 1.000
- **Mean Similarity:** 1.000
- **Total Documents:** 5

#### Confidence Calibration

| Confidence Bin | Samples | Mean Correctness |
|----------------|---------|------------------|
| 0.9-1.0 | 3 | 1.000 |
| 0.8-0.9 | 1 | 1.000 |
| 0.7-0.8 | 1 | 1.000 |

### bill_to_address

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### business_number

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### contract_id

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### customer_email

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### customer_fax

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### customer_phone

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### delivery_date

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### deposit_amount

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### discount_amount

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### entity

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### gst_amount

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### gst_number

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### gst_rate

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### handling_fee

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### hst_amount

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### hst_rate

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### invoice_type

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### payment_due_upon

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### payment_method

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### pst_amount

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### pst_number

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### pst_rate

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### qst_amount

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### qst_number

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### qst_rate

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### reference_number

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### remit_to_address

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### remit_to_name

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### shipping_amount

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### shipping_date

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### standing_offer_number

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### tax_breakdown

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### tax_registration_number

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### vendor_address

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### vendor_email

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### vendor_fax

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### vendor_id

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### vendor_phone

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5

### vendor_website

- **True Positives:** 0
- **False Positives:** 0
- **False Negatives:** 0
- **True Negatives:** 5
- **Precision:** 0.000
- **Recall:** 0.000
- **F1 Score:** 0.000
- **Accuracy:** 1.000
- **Exact Match Accuracy:** 0.000
- **Tolerant Match Accuracy:** 0.000
- **Mean Similarity:** 0.000
- **Total Documents:** 5
