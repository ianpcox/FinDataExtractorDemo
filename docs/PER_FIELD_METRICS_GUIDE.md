# Comprehensive Extraction Metrics Guide

This guide explains how to use the comprehensive per-field and document-level metrics system for evaluating invoice extraction performance.

## Overview

The comprehensive metrics system provides detailed evaluation metrics at two levels:

### Per-Field Metrics

Detailed evaluation metrics for each canonical field, including:

- **Precision/Recall/F1**: Standard classification metrics per field
- **Exact-Match Accuracy**: Percentage of documents where extracted value exactly matches ground truth
- **Value-Tolerant Accuracy**: For numeric/date fields, allows small tolerances (e.g., ±0.01 for amounts, ±0 days for dates)
- **String Similarity**: For text fields, calculates normalized similarity scores (0.0 to 1.0)
- **Confidence Calibration**: Analyzes whether confidence scores accurately reflect correctness

## Components

### 1. Field Metrics Calculator (`src/metrics/field_metrics.py`)

Core calculation engine that:
- Calculates confusion matrix components (TP, FP, FN, TN) per field
- Computes precision, recall, F1, and accuracy
- Performs exact and tolerant matching
- Calculates string similarity scores
- Tracks confidence calibration by binning confidence scores

### 2. Ground Truth Loader (`src/metrics/ground_truth_loader.py`)

Loads ground truth data from:
- CSV files (field_name, value, exists format)
- JSON files (nested structure with PDF names as keys)

### 3. Metrics Report Generator (`generate_per_field_metrics.py`)

Command-line script that:
- Loads extraction results from CSV
- Loads ground truth (optional)
- Calculates comprehensive metrics
- Generates Markdown report and CSV output

## Usage

### Basic Usage

```bash
python generate_per_field_metrics.py \
    --extraction-csv di_ocr_extraction_with_false_negatives.csv \
    --output per_field_metrics_report.md
```

### With Ground Truth

```bash
python generate_per_field_metrics.py \
    --extraction-csv di_ocr_extraction_with_false_negatives.csv \
    --ground-truth docs/ground_truth_template.csv \
    --output per_field_metrics_report.md
```

## Ground Truth Format

### CSV Format

```csv
pdf_name,field_name,value,exists
ACC012 4202092525.pdf,invoice_number,4202092525,true
ACC012 4202092525.pdf,invoice_date,2025-09-25,true
ACC012 4202092525.pdf,vendor_name,ACME Corporation,true
ACC012 4202092525.pdf,total_amount,1234.56,true
ACC012 4202092525.pdf,qst_number,,false
```

### JSON Format

```json
{
  "ACC012 4202092525.pdf": {
    "invoice_number": "4202092525",
    "invoice_date": "2025-09-25",
    "vendor_name": "ACME Corporation",
    "total_amount": 1234.56,
    "vendor_address": {
      "street": "123 Main St",
      "city": "Ottawa",
      "province": "ON",
      "postal_code": "K1A 0B1",
      "country": "Canada"
    }
  }
}
```

## Metrics Explained

### Precision

**Question**: "When I predict a value for this field, how often is it correct?"

**Formula**: `TP / (TP + FP)`

**Interpretation**: 
- 1.0 = Every extracted value is correct
- 0.5 = Half of extracted values are correct
- 0.0 = No extracted values are correct

### Recall

**Question**: "When the field exists in ground truth, how often do I extract it?"

**Formula**: `TP / (TP + FN)`

**Interpretation**:
- 1.0 = All existing fields are extracted
- 0.5 = Half of existing fields are extracted
- 0.0 = No existing fields are extracted

### F1 Score

**Question**: "What's the balanced performance considering both precision and recall?"

**Formula**: `2 * (Precision * Recall) / (Precision + Recall)`

**Interpretation**: Harmonic mean of precision and recall. Useful for sparse fields where extraction rate alone can be misleading.

### Exact-Match Accuracy

**Question**: "What percentage of documents have exactly correct values?"

**Formula**: `Exact Matches / Total Documents`

**Interpretation**: Strict correctness measure. Useful for fields where exact matching is critical (e.g., invoice numbers, tax IDs).

### Tolerant-Match Accuracy

**Question**: "What percentage of documents have values within acceptable tolerance?"

**Tolerances**:
- **Numeric fields**: ±0.01 absolute or ±0.1% relative
- **Date fields**: ±0 days (configurable)
- **Text fields**: ≥90% similarity
- **Address fields**: ≥70% of components match with ≥80% similarity each

**Interpretation**: More forgiving measure that accounts for minor variations (rounding, formatting).

### String Similarity

**Question**: "How similar are extracted text values to ground truth?"

**Method**: Normalized Levenshtein distance (SequenceMatcher ratio)

**Range**: 0.0 (completely different) to 1.0 (identical)

**Interpretation**: 
- 1.0 = Exact match
- 0.9 = Very similar (minor differences)
- 0.7 = Similar (some differences)
- <0.5 = Different

### Confidence Calibration

**Question**: "Does a confidence score of 0.9 actually mean 90% correctness?"

**Method**: Bins confidence scores and calculates mean correctness per bin

**Bins**:
- 0.9-1.0: High confidence
- 0.8-0.9: Medium-high confidence
- 0.7-0.8: Medium confidence
- 0.5-0.7: Low-medium confidence
- 0.0-0.5: Low confidence

**Interpretation**:
- Well-calibrated: Mean correctness ≈ bin center (e.g., 0.9 bin has ~0.9 correctness)
- Overconfident: Mean correctness < bin center (e.g., 0.9 bin has ~0.7 correctness)
- Underconfident: Mean correctness > bin center (e.g., 0.7 bin has ~0.9 correctness)

## Configuration

### Tolerances

You can adjust tolerances in `FieldMetricsCalculator`:

```python
calculator = FieldMetricsCalculator(
    numeric_tolerance=0.01,              # Absolute tolerance for amounts
    numeric_percentage_tolerance=0.001,  # 0.1% relative tolerance
    date_tolerance_days=0,               # Days tolerance for dates
)
```

### Field Type Detection

The system automatically detects field types:

- **Date fields**: `invoice_date`, `due_date`, `shipping_date`, `delivery_date`, `period_start`, `period_end`
- **Numeric fields**: `subtotal`, `tax_amount`, `total_amount`, `discount_amount`, `shipping_amount`, `handling_fee`, `deposit_amount`, `gst_amount`, `gst_rate`, `hst_amount`, `hst_rate`, `qst_amount`, `qst_rate`, `pst_amount`, `pst_rate`
- **Text fields**: `vendor_name`, `customer_name`, `invoice_number`, `po_number`, `vendor_address`, `bill_to_address`, `remit_to_address`

## Output Files

### Markdown Report (`per_field_metrics_report.md`)

Comprehensive report with:
- Summary statistics
- Metrics table (sorted by F1 score)
- Detailed metrics per field
- Confidence calibration tables

### CSV Report (`per_field_metrics_report.csv`)

Machine-readable metrics with columns:
- `field_name`
- `true_positives`, `false_positives`, `false_negatives`, `true_negatives`
- `precision`, `recall`, `f1_score`, `accuracy`
- `exact_match_accuracy`, `tolerant_match_accuracy`
- `mean_similarity`
- `total_documents`, `similarity_samples`

**Document Metrics CSV** (`*_document_metrics.csv`):

Machine-readable per-document metrics with columns:
- `pdf_name`
- `fields_extracted`, `total_fields`, `extraction_rate`
- `true_positives`, `false_positives`, `false_negatives`, `true_negatives`
- `precision`, `recall`, `f1_score`, `accuracy`
- `required_fields_correct`, `total_required_fields`, `all_required_fields_correct`
- `average_confidence`, `confidence_weighted_accuracy`
- `weighted_errors`, `weighted_f1`, `business_impact_score`

**Aggregate Metrics CSV** (`*_aggregate_metrics.csv`):

Summary statistics across all documents:
- `total_documents`
- `mean_extraction_rate`, `median_extraction_rate`
- `mean_precision`, `mean_recall`, `mean_f1`, `mean_accuracy`
- `hard_pass_count`, `hard_pass_rate`
- `mean_confidence`
- `mean_business_impact_score`, `mean_weighted_f1`

## Best Practices

1. **Use Real Ground Truth**: For production evaluation, always provide actual ground truth data. Using extraction results as ground truth (for testing) will show perfect scores.

2. **Review Confidence Calibration**: Check if confidence scores are well-calibrated. Overconfident models need threshold adjustment.

3. **Focus on Sparse Fields**: For fields that rarely appear (e.g., tax IDs), F1 score is more meaningful than extraction rate alone.

4. **Compare Tolerant vs Exact**: Large gap between tolerant and exact match accuracy indicates formatting/parsing issues.

5. **Monitor String Similarity**: Low similarity scores for text fields may indicate OCR quality issues or parsing problems.

## Integration with Test Scripts

To integrate with existing test scripts:

```python
from src.metrics.field_metrics import FieldMetricsCalculator
from src.metrics.ground_truth_loader import GroundTruthLoader

# Load ground truth
loader = GroundTruthLoader("ground_truth.csv")

# Calculate metrics
calculator = FieldMetricsCalculator()
metrics = calculator.calculate_metrics(
    extracted_data=extraction_results,
    ground_truth=ground_truth_data,
    field_names=all_field_names,
)

# Access per-field metrics
for field_name, field_metrics in metrics.items():
    print(f"{field_name}: F1={field_metrics.f1_score:.3f}")
```

## Troubleshooting

### All Metrics Show 0.0

- Check that ground truth format matches expected structure
- Verify field names match between extraction and ground truth
- Ensure PDF names match exactly

### Perfect Scores (1.0) for All Fields

- Likely using extraction results as ground truth (for testing)
- Provide actual ground truth data for real evaluation

### Low Similarity Scores

- Check for formatting differences (whitespace, case, punctuation)
- Verify address parsing is working correctly
- Review OCR quality for scanned documents

## Future Enhancements

Potential improvements:
- Support for line item metrics
- Temporal analysis (metrics over time)
- Field dependency analysis
- Automated threshold optimization
- Visualization (charts, graphs)
