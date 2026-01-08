# Confusion Matrix Analysis Report

## Overall Confusion Matrix


|                | Predicted: Extracted | Predicted: Not Extracted | Total |
|----------------|---------------------|-------------------------|-------|
| **Actual: Extracted** | 500 (TP) | 159 (FN) | 659 |
| **Actual: Not Extracted** |   0 (FP) |   5 (TN) |   5 |
| **Total** | 500 | 164 | 664 |


- **Precision:** 1.000 (TP / (TP + FP))
- **Recall:** 0.759 (TP / (TP + FN))
- **F1 Score:** 0.863 (harmonic mean of precision and recall)
- **Accuracy:** 0.761 ((TP + TN) / Total)

## Per-PDF Confusion Matrices

### ACC012 4202092525.pdf


|                | Predicted: Extracted | Predicted: Not Extracted | Total |
|----------------|---------------------|-------------------------|-------|
| **Actual: Extracted** |  25 (TP) |  28 (FN) |  53 |
| **Actual: Not Extracted** |   0 (FP) |   1 (TN) |   1 |
| **Total** |  25 |  29 |  54 |

- **Precision:** 1.000
- **Recall:** 0.472
- **F1 Score:** 0.641
- **Accuracy:** 0.481

### ANA005 90443097.pdf


|                | Predicted: Extracted | Predicted: Not Extracted | Total |
|----------------|---------------------|-------------------------|-------|
| **Actual: Extracted** |  28 (TP) |  29 (FN) |  57 |
| **Actual: Not Extracted** |   0 (FP) |   1 (TN) |   1 |
| **Total** |  28 |  30 |  58 |

- **Precision:** 1.000
- **Recall:** 0.491
- **F1 Score:** 0.659
- **Accuracy:** 0.500

### ENB001 166574659065NOV2025.pdf


|                | Predicted: Extracted | Predicted: Not Extracted | Total |
|----------------|---------------------|-------------------------|-------|
| **Actual: Extracted** |  32 (TP) |  34 (FN) |  66 |
| **Actual: Not Extracted** |   0 (FP) |   1 (TN) |   1 |
| **Total** |  32 |  35 |  67 |

- **Precision:** 1.000
- **Recall:** 0.485
- **F1 Score:** 0.653
- **Accuracy:** 0.493

### HYD001 5160530790NOV2025.pdf


|                | Predicted: Extracted | Predicted: Not Extracted | Total |
|----------------|---------------------|-------------------------|-------|
| **Actual: Extracted** |  34 (TP) |  37 (FN) |  71 |
| **Actual: Not Extracted** |   0 (FP) |   1 (TN) |   1 |
| **Total** |  34 |  38 |  72 |

- **Precision:** 1.000
- **Recall:** 0.479
- **F1 Score:** 0.648
- **Accuracy:** 0.486

### TEL006 4222600.pdf


|                | Predicted: Extracted | Predicted: Not Extracted | Total |
|----------------|---------------------|-------------------------|-------|
| **Actual: Extracted** | 381 (TP) |  31 (FN) | 412 |
| **Actual: Not Extracted** |   0 (FP) |   1 (TN) |   1 |
| **Total** | 381 |  32 | 413 |

- **Precision:** 1.000
- **Recall:** 0.925
- **F1 Score:** 0.961
- **Accuracy:** 0.925

## Per-Field Confusion Matrices (Top 20 by F1 Score)

| Field Name | TP | FP | FN | TN | Precision | Recall | F1 Score | Accuracy |
|------------|----|----|----|----|-----------|--------|----------|----------|
| `vendor_phone` | 5 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bill_to_address` | 5 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `vendor_name` | 5 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `vendor_address` | 5 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `total_amount` | 5 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_99` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_98` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_97` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_96` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_95` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_94` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_93` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_92` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_91` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_90` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_110` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_11` | 3 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_109` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_108` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `line_item_107` | 1 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |

## Per-Field Confusion Matrices (Bottom 20 by F1 Score)

| Field Name | TP | FP | FN | TN | Precision | Recall | F1 Score | Accuracy |
|------------|----|----|----|----|-----------|--------|----------|----------|
| `hst_amount` | 1 | 0 | 4 | 0 | 1.000 | 0.200 | 0.333 | 0.200 |
| `customer_phone` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `customer_fax` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `discount_amount` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `handling_fee` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `delivery_date` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `deposit_amount` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `shipping_amount` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `qst_number` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `hst_rate` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `qst_rate` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `shipping_date` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `tax_registration_number` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `tax_breakdown` | 0 | 0 | 0 | 5 | 0.000 | 0.000 | 0.000 | 1.000 |
| `payment_method` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `invoice_type` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `payment_due_upon` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `customer_email` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `contract_id` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `vendor_id` | 0 | 0 | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |