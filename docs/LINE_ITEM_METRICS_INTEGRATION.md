# Line Item Metrics Integration

## Overview

Line item-specific metrics have been added to the metrics system to provide comprehensive evaluation of line item extraction, aggregation validation, and per-line-item field accuracy.

## Components Added

### 1. Line Item Metrics Module (`src/metrics/line_item_metrics.py`)

A comprehensive module for calculating line item-specific metrics:

#### **LineItemFieldMetrics**
Metrics for individual line item fields (description, quantity, unit_price, amount, taxes, etc.):
- Precision, Recall, F1 Score
- Exact match accuracy
- Tolerant match accuracy (within 1 cent tolerance for numeric fields)
- String similarity scores (for text fields like description)
- Confusion matrix components (TP, FP, FN, TN)

#### **LineItemCountMetrics**
Metrics for line item count per document:
- Extracted count vs ground truth count
- Count match (exact match)
- Count difference
- Count accuracy (ratio-based)

#### **AggregationMetrics**
Metrics for aggregation validation (invoice totals = sum of line items):
- Subtotal validation
- GST/PST/QST amount validation
- Tax amount validation
- Total amount validation
- Validation score (percentage of validations passed)
- Difference values when validation fails

#### **LineItemMetricsCalculator**
Main calculator class that:
- Matches extracted line items with ground truth by line_number
- Calculates per-field metrics for all line item fields
- Calculates count metrics per document
- Calculates aggregation validation metrics
- Handles numeric tolerance (1 cent for financial fields)
- Calculates string similarity for text fields

### 2. Integration with Metrics Generation (`generate_per_field_metrics.py`)

The metrics generation script has been updated to:
- Import and use `LineItemMetricsCalculator`
- Calculate line item metrics alongside field and document metrics
- Include line item metrics sections in the report
- Export line item metrics to separate CSV files

## Metrics Calculated

### Per-Line-Item Field Metrics
For each line item field (description, quantity, unit_price, amount, taxes, etc.):
- **Precision**: When a field is extracted, how often is it correct?
- **Recall**: When a field exists in ground truth, how often is it extracted?
- **F1 Score**: Balanced measure of precision and recall
- **Accuracy**: Overall correctness
- **Exact Match Accuracy**: Percentage of exact matches
- **Tolerant Match Accuracy**: Percentage of matches within tolerance (for numeric fields)
- **Mean Similarity**: Average string similarity (for text fields)

### Line Item Count Metrics
Per document:
- **Extracted Count**: Number of line items extracted
- **Ground Truth Count**: Number of line items in ground truth
- **Count Match**: Whether counts match exactly
- **Count Accuracy**: Ratio-based accuracy of count

### Aggregation Validation Metrics
Per document:
- **Subtotal Valid**: `invoice.subtotal == sum(line_item.amount)`
- **GST Amount Valid**: `invoice.gst_amount == sum(line_item.gst_amount)`
- **PST Amount Valid**: `invoice.pst_amount == sum(line_item.pst_amount)`
- **QST Amount Valid**: `invoice.qst_amount == sum(line_item.qst_amount)`
- **Tax Amount Valid**: `invoice.tax_amount == sum(line_item.tax_amount)`
- **Total Amount Valid**: `invoice.total_amount == subtotal + tax + shipping + handling - discount`
- **All Valid**: All aggregations passed
- **Validation Score**: Percentage of validations that passed

## Report Sections

The metrics report now includes three new sections:

### 1. Line Item Count Metrics
Table showing per-document line item count comparison with summary statistics.

### 2. Line Item Field Metrics
Table showing per-field metrics for all line item fields, sorted by F1 score.

### 3. Aggregation Validation Metrics
Table showing per-document aggregation validation results with summary statistics.

## CSV Exports

Three new CSV files are generated:

1. **`*_line_item_count_metrics.csv`**: Line item count metrics per document
2. **`*_line_item_field_metrics.csv`**: Per-field metrics for line item fields
3. **`*_line_item_aggregation_metrics.csv`**: Aggregation validation metrics per document

## Usage

Line item metrics are automatically calculated when running:

```bash
python generate_per_field_metrics.py --extraction-csv <path> --ground-truth <path> --output <path>
```

The metrics require:
- **Extraction results** with `line_items` array in each document
- **Ground truth** with `line_items` array in each document

### Expected Data Format

**Extraction Results:**
```json
{
  "pdf_name": "invoice.pdf",
  "extracted_fields": {...},
  "line_items": [
    {
      "line_number": 1,
      "description": "Item A",
      "quantity": "10",
      "unit_price": "50.00",
      "amount": "500.00",
      "gst_amount": "25.00",
      "pst_amount": "35.00",
      "tax_amount": "60.00",
      "confidence": 0.90
    }
  ]
}
```

**Ground Truth:**
```json
{
  "pdf_name": "invoice.pdf",
  "line_items": [
    {
      "line_number": 1,
      "description": "Item A",
      "quantity": "10",
      "unit_price": "50.00",
      "amount": "500.00",
      "gst_amount": "25.00",
      "pst_amount": "35.00",
      "tax_amount": "60.00"
    }
  ]
}
```

## Benefits

1. **Comprehensive Evaluation**: Evaluates both individual line item fields and aggregation consistency
2. **Nested Testing Support**: Aligns with the nested testing architecture (Tier 2: Line Items, Tier 3: Aggregation)
3. **Actionable Insights**: Identifies specific fields and documents with extraction issues
4. **Aggregation Validation**: Automatically validates that invoice totals match line item sums
5. **Detailed Reporting**: Provides both summary and detailed metrics for analysis

## Integration with Existing Metrics

Line item metrics complement the existing metrics system:
- **Field Metrics**: Evaluates invoice-level fields
- **Document Metrics**: Evaluates document-level extraction
- **Line Item Metrics**: Evaluates line item-level extraction and aggregation (NEW)

Together, these provide a complete picture of extraction performance at all levels.

## Future Enhancements

1. **Line Item Confidence Calibration**: Track confidence calibration for line item fields
2. **Line Item Matching Algorithms**: Improve matching when line numbers don't align
3. **Per-Line-Item Business Impact**: Weight line item errors by importance
4. **Line Item Coverage Metrics**: Track which line item fields are most commonly extracted
5. **Aggregation Auto-Correction**: Optionally correct minor aggregation discrepancies
