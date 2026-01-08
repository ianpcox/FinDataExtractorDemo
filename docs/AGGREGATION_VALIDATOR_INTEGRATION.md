# AggregationValidator Integration

## Overview

The `AggregationValidator` has been fully integrated into the `ExtractionService` to automatically validate financial consistency between invoice-level totals and line item sums during the extraction process.

## Integration Points

### 1. Initial Extraction Validation

After extracting invoice data and line items, the service automatically runs aggregation validation:

```python
# Validate aggregation consistency (invoice totals = sum of line items)
aggregation_validation = None
if invoice.line_items:
    aggregation_validation = AggregationValidator.get_validation_summary(invoice)
    if not aggregation_validation["all_valid"]:
        logger.warning(
            f"Aggregation validation failed for invoice {invoice_id}: "
            f"{aggregation_validation['failed_validations']} validation(s) failed"
        )
        for error in aggregation_validation["errors"]:
            logger.warning(f"  - {error}")
    else:
        logger.info(
            f"Aggregation validation passed for invoice {invoice_id}: "
            f"all {aggregation_validation['total_validations']} validations passed"
        )
```

**Location**: `src/extraction/extraction_service.py` lines 342-356

### 2. Post-LLM Validation

After LLM post-processing (if changes were made), aggregation validation is re-run to ensure consistency:

```python
# Re-run aggregation validation after LLM changes
if invoice.line_items:
    aggregation_validation = AggregationValidator.get_validation_summary(invoice)
    # Log results...
```

**Location**: `src/extraction/extraction_service.py` lines 610-625

### 3. Extraction Result

Aggregation validation results are included in the extraction response:

```python
result = {
    "invoice_id": invoice_id,
    "status": "extracted",
    "invoice": invoice_dict,
    "confidence": invoice.extraction_confidence,
    "field_confidence": invoice.field_confidence,
    "extraction_timestamp": extraction_ts,
    "errors": [],
    "low_confidence_fields": low_conf_fields,
    "low_confidence_triggered": bool(low_conf_fields),
    "validation": validation_result,  # Business rule validation
    "aggregation_validation": aggregation_validation  # Aggregation validation
}
```

**Location**: `src/extraction/extraction_service.py` lines 620-631

## Validation Checks

The `AggregationValidator` performs the following checks:

1. **Subtotal Validation**: `invoice.subtotal == sum(line_item.amount)`
2. **GST Amount Validation**: `invoice.gst_amount == sum(line_item.gst_amount)`
3. **PST Amount Validation**: `invoice.pst_amount == sum(line_item.pst_amount)`
4. **QST Amount Validation**: `invoice.qst_amount == sum(line_item.qst_amount)`
5. **Tax Amount Validation**: `invoice.tax_amount == sum(line_item.tax_amount)` or sum of individual taxes
6. **Total Amount Validation**: `invoice.total_amount == subtotal + tax + shipping + handling - discount`

All validations use a tolerance of **$0.01** (1 cent) to account for rounding differences.

## Validation Summary Structure

The `aggregation_validation` object in the extraction result contains:

```python
{
    "all_valid": bool,  # True if all validations passed
    "validations": {
        "subtotal": (is_valid, error_message),
        "gst_amount": (is_valid, error_message),
        "pst_amount": (is_valid, error_message),
        "qst_amount": (is_valid, error_message),
        "tax_amount": (is_valid, error_message),
        "total_amount": (is_valid, error_message),
    },
    "errors": [str],  # List of error messages for failed validations
    "total_validations": int,  # Total number of validations (6)
    "passed_validations": int,  # Number of validations that passed
    "failed_validations": int,  # Number of validations that failed
}
```

## Behavior

### Non-Blocking

Aggregation validation is **non-blocking**:
- Validation failures are logged as warnings
- Extraction continues even if validation fails
- Results are included in the response for downstream processing

### When Validation Runs

1. **After Initial Extraction**: When invoice and line items are first extracted
2. **After LLM Post-Processing**: If LLM makes changes to the invoice data

### When Validation is Skipped

- If `invoice.line_items` is empty or None
- If no line items were extracted

## Logging

### Success Case
```
INFO: Aggregation validation passed for invoice {invoice_id}: all 6 validations passed
```

### Failure Case
```
WARNING: Aggregation validation failed for invoice {invoice_id}: 2 validation(s) failed
WARNING:   - Subtotal mismatch: invoice.subtotal=1000.00 != sum(line_item.amount)=999.99, difference=0.01
WARNING:   - Tax amount mismatch: invoice.tax_amount=130.00 != sum(line_item.tax_amount)=129.99, difference=0.01
```

## Usage in Downstream Systems

Downstream systems can check aggregation validation results:

```python
result = await extraction_service.extract_invoice(...)

if result.get("aggregation_validation"):
    agg_val = result["aggregation_validation"]
    if not agg_val["all_valid"]:
        # Handle aggregation failures
        for error in agg_val["errors"]:
            # Log or alert on aggregation issues
            pass
```

## Benefits

1. **Automatic Validation**: No manual intervention required
2. **Early Detection**: Issues are identified immediately after extraction
3. **Comprehensive**: Validates all financial aggregations
4. **Non-Blocking**: Doesn't interrupt the extraction workflow
5. **Detailed Reporting**: Provides specific error messages for each validation
6. **Integration Ready**: Results included in extraction response for downstream use

## Future Enhancements

1. **Auto-Correction**: Optionally correct minor discrepancies automatically
2. **Confidence Scoring**: Include aggregation validation in overall confidence score
3. **Metrics Integration**: Track aggregation validation pass/fail rates
4. **Alerting**: Send alerts for critical aggregation failures
5. **Historical Tracking**: Track aggregation validation trends over time
