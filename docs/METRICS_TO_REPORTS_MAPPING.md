# Metrics to Reports Mapping

This document explains how metrics are mapped to existing reports and ensures consistency across the evaluation system.

## Overview

The metrics system is designed to align with existing reports:

1. **Extraction Rate** → Already in `comprehensive_extraction_test_report.md` and remains a top-level document metric
2. **Overall Confidence** → Already present; used alongside correctness to build calibration metrics
3. **Field Coverage** → Defined in canonical field coverage reports (53 fields); used as denominator for all metrics

## Metric Mappings

### 1. Extraction Rate

**Location**: `comprehensive_extraction_test_report.md` and `comprehensive_metrics_report.md`

**Definition**: Percentage of canonical fields extracted per document

**Formula**: `Fields Extracted / 53 canonical fields`

**Example**: 
- 11 fields extracted out of 53 = 20.8%
- Reported as: "Extraction Rate: 20.8%" and "Fields Extracted: 11/53"

**Usage**: 
- Coverage metric (not accuracy)
- Top-level document metric in both reports
- Denominator is always 53 (from canonical field coverage reports)

### 2. Overall Confidence

**Location**: `comprehensive_extraction_test_report.md` and `comprehensive_metrics_report.md`

**Definition**: Mean confidence score across all extracted fields in a document

**Formula**: `Sum of Field Confidences / Number of Extracted Fields`

**Usage**:
- Already captured per document
- Used for regression and monitoring
- **Paired with accuracy metrics** to build confidence calibration:
  - Expected Calibration Error (ECE)
  - Max Calibration Error (MCE)
  - Calibration Slope (correlation)
  - Per-bin calibration analysis

**Calibration Metrics**:
- **ECE**: Weighted average of |confidence - correctness| across bins
- **MCE**: Maximum |confidence - correctness| across all bins
- **Slope**: Correlation coefficient between confidence and correctness

### 3. Field Coverage (Canonical Fields)

**Location**: Canonical field coverage reports:
- `DI_CANONICAL_FIELD_COVERAGE_REPORT.md`
- `LLM_CANONICAL_FIELD_COVERAGE_REPORT.md`
- `MULTIMODAL_LLM_CANONICAL_FIELD_COVERAGE_REPORT.md`

**Definition**: Total number of canonical fields (53 fields)

**Source**: `CANONICAL_FIELDS` in `src/extraction/extraction_service.py`

**Usage**:
- **Denominator for extraction rate**: `fields_extracted / 53`
- **Denominator for per-field metrics**: All metrics calculated against 53 fields
- **Denominator for document-level metrics**: All document metrics use 53 as total_fields

**Consistency**: 
- All metrics use the same canonical field count (53)
- Ensures extraction rates are comparable across methods (DI OCR, Base LLM, Multimodal LLM)
- Field coverage reports define which fields are extractable by each method

## Report Structure

### comprehensive_extraction_test_report.md

**Purpose**: Compare extraction methods (DI OCR, Base LLM, Multimodal LLM)

**Metrics**:
- Extraction Rate (per method, per document)
- Overall Confidence (per method, per document)
- Fields Extracted (X/53 format)
- Duration (for DI OCR)

**Structure**:
- Executive Summary table
- Per-PDF breakdown
- Method comparison averages

### comprehensive_metrics_report.md

**Purpose**: Comprehensive evaluation with ground truth comparison

**Metrics**:
- **Document-Level**:
  - Extraction Rate (using 53 as denominator)
  - Accuracy/F1 (micro-averaged)
  - Hard Pass Rate (all required fields correct)
  - Overall Confidence
  - Business Impact Score
  - Confidence Calibration (ECE, MCE, Slope)
- **Per-Field**:
  - Precision/Recall/F1
  - Exact/Tolerant Match Accuracy
  - String Similarity
  - Confidence Calibration (per field)

**Structure**:
- Summary with canonical field count (53)
- Document-level summary
- Confidence calibration section
- Document-level metrics table
- Per-field metrics table
- Detailed per-field metrics

## Consistency Rules

### 1. Canonical Field Count

**Rule**: Always use 53 as the denominator for extraction rate calculations.

**Implementation**:
- Source: `src/metrics/metrics_config.py` → `get_canonical_field_count()`
- Used in: `DocumentMetricsCalculator`, `generate_per_field_metrics.py`
- Verified against: `CANONICAL_FIELDS` in `extraction_service.py`

### 2. Extraction Rate Format

**Rule**: Always report as "X/Y (Z%)" where Y = 53.

**Examples**:
- "11/53 (20.8%)"
- "22/53 (41.5%)"

**Location**: Both `comprehensive_extraction_test_report.md` and `comprehensive_metrics_report.md`

### 3. Overall Confidence

**Rule**: Always pair overall confidence with correctness metrics.

**Implementation**:
- Document-level: Mean overall confidence + calibration metrics
- Per-field: Confidence bins with mean correctness
- Calibration: ECE, MCE, Slope calculated from confidence-correctness pairs

### 4. Field Coverage

**Rule**: Field coverage is defined in canonical field coverage reports, not calculated.

**Implementation**:
- 53 fields defined in `CANONICAL_FIELDS`
- Coverage reports document which fields are extractable by each method
- Metrics use 53 as denominator regardless of method

## Integration Points

### Metrics Configuration

**File**: `src/metrics/metrics_config.py`

**Purpose**: Single source of truth for:
- Canonical field count (53)
- Required fields for hard pass
- Field importance weights
- Field definitions

**Usage**: Imported by all metrics calculators to ensure consistency.

### Confidence Calibration

**File**: `src/metrics/confidence_calibration.py`

**Purpose**: Calculate calibration metrics using overall confidence and correctness.

**Inputs**:
- Overall confidence per document
- Document-level correctness (from ground truth comparison)

**Outputs**:
- Expected Calibration Error (ECE)
- Max Calibration Error (MCE)
- Calibration Slope
- Per-bin calibration data

### Document Metrics

**File**: `src/metrics/document_metrics.py`

**Purpose**: Calculate document-level metrics using canonical field count.

**Key Features**:
- Uses 53 as `total_fields` (from `metrics_config`)
- Calculates extraction rate: `fields_extracted / 53`
- Calculates business impact using field weights
- Tracks required fields for hard pass evaluation

## Best Practices

1. **Always use canonical field count**: Import from `metrics_config.get_canonical_field_count()` rather than hardcoding.

2. **Report extraction rate consistently**: Always show "X/53 (Z%)" format.

3. **Pair confidence with correctness**: Never report overall confidence without calibration metrics.

4. **Reference canonical field coverage**: When discussing field coverage, reference the appropriate coverage report (DI, LLM, or Multimodal LLM).

5. **Use field coverage as denominator**: All extraction rates use 53 as denominator, regardless of which fields are actually extractable by a given method.

## Example Usage

```python
from src.metrics.metrics_config import get_canonical_field_count
from src.metrics.document_metrics import DocumentMetricsCalculator
from src.metrics.confidence_calibration import ConfidenceCalibrationCalculator

# Get canonical field count (53)
canonical_field_count = get_canonical_field_count()

# Calculate document metrics (uses 53 as denominator)
doc_calculator = DocumentMetricsCalculator(canonical_field_count=canonical_field_count)
doc_metrics = doc_calculator.calculate_metrics(extracted_data, ground_truth, field_names)

# Calculate confidence calibration (uses overall confidence)
calibration_calculator = ConfidenceCalibrationCalculator()
calibration_metrics = calibration_calculator.calculate_calibration(
    extracted_data, ground_truth, field_names
)
```

## Report Alignment

### comprehensive_extraction_test_report.md

- **Extraction Rate**: Top-level metric, uses 53 as denominator
- **Overall Confidence**: Per document, per method
- **Fields Extracted**: X/53 format

### comprehensive_metrics_report.md

- **Extraction Rate**: Document-level summary, uses 53 as denominator
- **Overall Confidence**: Mean across documents, with calibration metrics
- **Field Coverage**: Explicitly stated as 53 canonical fields
- **Confidence Calibration**: Detailed analysis with bins and gaps

### Canonical Field Coverage Reports

- **Field Count**: 53 canonical fields (explicitly documented)
- **Coverage**: Which fields are extractable by each method
- **Used As**: Reference for field coverage definitions

## Summary

All metrics are now consistently mapped:

1. ✅ **Extraction Rate** → Top-level document metric in both reports, uses 53 as denominator
2. ✅ **Overall Confidence** → Present in both reports, paired with calibration metrics
3. ✅ **Field Coverage** → 53 fields from canonical field coverage reports, used as denominator for all metrics

This ensures consistency across all evaluation reports and metrics calculations.
