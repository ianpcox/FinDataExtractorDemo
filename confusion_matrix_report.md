# Confusion Matrix Analysis Report

## Overall Confusion Matrix


|                | Predicted: Extracted | Predicted: Not Extracted | Total |
|----------------|---------------------|-------------------------|-------|
| **Actual: Extracted** |  45 (TP) |  15 (FN) |  60 |
| **Actual: Not Extracted** |  10 (FP) | 195 (TN) | 205 |
| **Total** |  55 | 210 | 265 |


- **Precision:** 0.818 (TP / (TP + FP))
- **Recall:** 0.750 (TP / (TP + FN))
- **F1 Score:** 0.783 (harmonic mean of precision and recall)
- **Accuracy:** 0.906 ((TP + TN) / Total)

## Per-PDF Confusion Matrices

### ACC012 4202092525.pdf


|                | Predicted: Extracted | Predicted: Not Extracted | Total |
|----------------|---------------------|-------------------------|-------|
| **Actual: Extracted** |  10 (TP) |   1 (FN) |  11 |
| **Actual: Not Extracted** |   2 (FP) |  40 (TN) |  42 |
| **Total** |  12 |  41 |  53 |

- **Precision:** 0.833
- **Recall:** 0.909
- **F1 Score:** 0.870
- **Accuracy:** 0.943

### ANA005 90443097.pdf


|                | Predicted: Extracted | Predicted: Not Extracted | Total |
|----------------|---------------------|-------------------------|-------|
| **Actual: Extracted** |  10 (TP) |   3 (FN) |  13 |
| **Actual: Not Extracted** |   1 (FP) |  39 (TN) |  40 |
| **Total** |  11 |  42 |  53 |

- **Precision:** 0.909
- **Recall:** 0.769
- **F1 Score:** 0.833
- **Accuracy:** 0.925

### ENB001 166574659065NOV2025.pdf


|                | Predicted: Extracted | Predicted: Not Extracted | Total |
|----------------|---------------------|-------------------------|-------|
| **Actual: Extracted** |   8 (TP) |   3 (FN) |  11 |
| **Actual: Not Extracted** |   3 (FP) |  39 (TN) |  42 |
| **Total** |  11 |  42 |  53 |

- **Precision:** 0.727
- **Recall:** 0.727
- **F1 Score:** 0.727
- **Accuracy:** 0.887

### HYD001 5160530790NOV2025.pdf


|                | Predicted: Extracted | Predicted: Not Extracted | Total |
|----------------|---------------------|-------------------------|-------|
| **Actual: Extracted** |   7 (TP) |   5 (FN) |  12 |
| **Actual: Not Extracted** |   1 (FP) |  40 (TN) |  41 |
| **Total** |   8 |  45 |  53 |

- **Precision:** 0.875
- **Recall:** 0.583
- **F1 Score:** 0.700
- **Accuracy:** 0.887

### TEL006 4222600.pdf


|                | Predicted: Extracted | Predicted: Not Extracted | Total |
|----------------|---------------------|-------------------------|-------|
| **Actual: Extracted** |  10 (TP) |   3 (FN) |  13 |
| **Actual: Not Extracted** |   3 (FP) |  37 (TN) |  40 |
| **Total** |  13 |  40 |  53 |

- **Precision:** 0.769
- **Recall:** 0.769
- **F1 Score:** 0.769
- **Accuracy:** 0.887

## Per-Field Confusion Matrices (Top 20 by F1 Score)

| Field Name | TP | FP | FN | TN | Precision | Recall | F1 Score | Accuracy |
|------------|----|----|----|----|-----------|--------|----------|----------|
| `due_date` | 4 | 0 | 0 | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| `po_number` | 3 | 0 | 0 | 2 | 1.000 | 1.000 | 1.000 | 1.000 |
| `vendor_name` | 5 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `invoice_date` | 5 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `invoice_number` | 3 | 0 | 0 | 2 | 1.000 | 1.000 | 1.000 | 1.000 |
| `customer_id` | 4 | 0 | 0 | 1 | 1.000 | 1.000 | 1.000 | 1.000 |
| `customer_name` | 5 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `payment_terms` | 2 | 0 | 0 | 3 | 1.000 | 1.000 | 1.000 | 1.000 |
| `tax_amount` | 5 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `total_amount` | 5 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `subtotal` | 4 | 0 | 1 | 0 | 1.000 | 0.800 | 0.889 | 0.800 |
| `remit_to_address` | 0 | 0 | 4 | 1 | 0.000 | 0.000 | 0.000 | 0.200 |
| `qst_rate` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `reference_number` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `shipping_amount` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `qst_number` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `qst_amount` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `remit_to_name` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `bill_to_address` | 0 | 0 | 3 | 2 | 0.000 | 0.000 | 0.000 | 0.400 |
| `shipping_date` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |

## Per-Field Confusion Matrices (Bottom 20 by F1 Score)

| Field Name | TP | FP | FN | TN | Precision | Recall | F1 Score | Accuracy |
|------------|----|----|----|----|-----------|--------|----------|----------|
| `contract_id` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `currency` | 0 | 5 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `customer_email` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `customer_fax` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `customer_phone` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `delivery_date` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `deposit_amount` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `discount_amount` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `entity` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `gst_amount` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `gst_number` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `gst_rate` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `handling_fee` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `hst_amount` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `hst_rate` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `invoice_type` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `payment_due_upon` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `payment_method` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `business_number` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `vendor_website` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |