# Managing False Negatives in Extraction Tests

## Understanding False Negatives

A **false negative** occurs when:
1. A field **should be extractable** from the document but is marked as **not extracted**
2. A field **has a value** but the test logic incorrectly marks it as **missing**
3. A field **could be extracted** but the extraction method didn't find it

## Common Causes of False Negatives

### 1. **Strict Extraction Logic**

The current extraction detection logic may be too strict:

```python
# Current logic in test files
if isinstance(field_value, str):
    is_extracted = field_value.strip() != ""  # Empty strings = not extracted
elif isinstance(field_value, (int, float, Decimal)):
    is_extracted = field_value != 0  # Zero values = not extracted
```

**Problem:** Fields with legitimate zero values or empty strings are marked as not extracted.

### 2. **Confidence Threshold Issues**

Fields with low confidence (< 0.75) may be marked as not extracted even if they have values:

```python
extracted_by_di = confidence is not None and confidence >= low_conf_threshold
```

**Problem:** A field might have a value but low confidence, so it's not counted as "extracted by DI".

### 3. **Field Mapping Gaps**

DI field names might not map correctly to canonical fields, causing valid extractions to be missed.

### 4. **Value Format Issues**

- Dates in unexpected formats
- Numbers as strings
- Addresses in different structures
- Line items not properly parsed

## Strategies for Managing False Negatives

### Strategy 1: Review Field-by-Field CSV

Use `comprehensive_extraction_field_details.csv` to identify false negatives:

```python
import pandas as pd

# Load the CSV
df = pd.read_csv('comprehensive_extraction_field_details.csv')

# Find fields marked as not extracted but have values
false_negatives = df[
    (df['best_extracted'] == False) & 
    (
        (df['di_value'].notna() & (df['di_value'] != '')) |
        (df['llm_value'].notna() & (df['llm_value'] != '')) |
        (df['multimodal_value'].notna() & (df['multimodal_value'] != ''))
    )
]

print(f"Found {len(false_negatives)} potential false negatives")
print(false_negatives[['pdf_name', 'field_name', 'di_value', 'llm_value', 'multimodal_value']])
```

### Strategy 2: Adjust Extraction Detection Logic

Modify the extraction detection to be more lenient:

```python
# In test_di_ocr_extraction_standalone.py, test_llm_extraction_standalone.py, etc.

def is_field_extracted(field_value, field_name=None):
    """
    Determine if a field is extracted, with special handling for false negatives.
    
    Args:
        field_value: The field value to check
        field_name: Optional field name for special cases
        
    Returns:
        bool: True if field is considered extracted
    """
    if field_value is None:
        return False
    
    # Special handling for different types
    if isinstance(field_value, str):
        # Consider extracted if non-empty (even if just whitespace might be trimmed)
        return field_value.strip() != ""
    
    elif isinstance(field_value, (int, float, Decimal)):
        # For numeric fields, 0 might be a valid value
        # Check if it's a field that can legitimately be 0
        zero_allowed_fields = ['discount_amount', 'deposit_amount', 'handling_fee', 'shipping_amount']
        if field_name in zero_allowed_fields:
            return True  # 0 is a valid value
        return field_value != 0
    
    elif isinstance(field_value, dict):
        # Address or complex object - check if it has meaningful content
        if not field_value:
            return False
        # Check if address has at least one component
        if 'street' in field_value or 'city' in field_value or 'postal_code' in field_value:
            return True
        return len(field_value) > 0
    
    elif isinstance(field_value, list):
        # Line items or arrays
        return len(field_value) > 0
    
    elif hasattr(field_value, 'isoformat'):
        # Date/datetime objects - always extracted if present
        return True
    
    else:
        # Other types - consider extracted if not None
        return True
```

### Strategy 3: Lower Confidence Thresholds for Detection

Adjust confidence thresholds to catch more extractions:

```python
# In test files, modify the confidence threshold
low_conf_threshold = 0.5  # Instead of 0.75, use 0.5 for detection

# Or use different thresholds for different purposes
extraction_detection_threshold = 0.5  # Lower threshold for "was it extracted?"
quality_threshold = 0.75  # Higher threshold for "is it high quality?"
```

### Strategy 4: Manual Review Script

Create a script to help identify false negatives:

```python
"""
Script to identify and review false negatives in extraction tests.
"""

import pandas as pd
from pathlib import Path

def identify_false_negatives(csv_path='comprehensive_extraction_field_details.csv'):
    """Identify potential false negatives."""
    df = pd.read_csv(csv_path)
    
    # Potential false negatives: marked as not extracted but have values
    false_negatives = []
    
    for _, row in df.iterrows():
        if row['best_extracted'] == False:
            # Check if any method found a value
            has_di_value = pd.notna(row['di_value']) and str(row['di_value']).strip() != ''
            has_llm_value = pd.notna(row['llm_value']) and str(row['llm_value']).strip() != ''
            has_multimodal_value = pd.notna(row['multimodal_value']) and str(row['multimodal_value']).strip() != ''
            
            if has_di_value or has_llm_value or has_multimodal_value:
                false_negatives.append({
                    'pdf_name': row['pdf_name'],
                    'field_name': row['field_name'],
                    'di_value': row['di_value'],
                    'llm_value': row['llm_value'],
                    'multimodal_value': row['multimodal_value'],
                    'di_confidence': row['di_confidence'],
                    'llm_confidence': row['llm_confidence'],
                    'multimodal_confidence': row['multimodal_confidence'],
                })
    
    return pd.DataFrame(false_negatives)

def review_false_negatives():
    """Review and categorize false negatives."""
    fn_df = identify_false_negatives()
    
    if len(fn_df) == 0:
        print("No false negatives found!")
        return
    
    print(f"Found {len(fn_df)} potential false negatives\n")
    
    # Group by field name
    by_field = fn_df.groupby('field_name').size().sort_values(ascending=False)
    print("False negatives by field:")
    print(by_field)
    
    # Group by PDF
    by_pdf = fn_df.groupby('pdf_name').size().sort_values(ascending=False)
    print("\nFalse negatives by PDF:")
    print(by_pdf)
    
    # Save detailed report
    fn_df.to_csv('false_negatives_report.csv', index=False)
    print(f"\nDetailed report saved to: false_negatives_report.csv")
    
    return fn_df

if __name__ == "__main__":
    review_false_negatives()
```

### Strategy 5: Improve Field Mapping

Review and improve DI field mappings:

```python
# Check if DI fields are being mapped correctly
# In test_di_ocr_extraction_standalone.py, review di_field_sources

# Add more DI field name variants to FieldExtractor.DI_TO_CANONICAL
# Example: If "CustomerID" and "Customer Id" both exist, map both
```

### Strategy 6: Manual Validation

For critical false negatives, manually validate:

1. **Open the PDF** and check if the field is actually present
2. **Check the DI raw output** to see if DI found it but didn't map it
3. **Check the LLM response** to see if LLM found it but didn't apply it
4. **Review the extraction logic** to see why it wasn't detected

### Strategy 7: Adjust Test Expectations

Some fields may legitimately not be extractable from certain documents:

```python
# Create a field availability matrix
# Some fields are only available in certain invoice types

OPTIONAL_FIELDS = {
    'contract_id': ['contract_invoices'],  # Only in contract-based invoices
    'standing_offer_number': ['government_invoices'],
    'gst_number': ['canadian_invoices'],
    # etc.
}

# Adjust extraction rate calculation to exclude unavailable fields
```

## Implementation Steps

### Step 1: Run False Negative Detection

```bash
python -c "
import pandas as pd
df = pd.read_csv('comprehensive_extraction_field_details.csv')
fn = df[(df['best_extracted'] == False) & (
    (df['di_value'].notna() & (df['di_value'] != '')) |
    (df['llm_value'].notna() & (df['llm_value'] != '')) |
    (df['multimodal_value'].notna() & (df['multimodal_value'] != ''))
)]
print(f'Potential false negatives: {len(fn)}')
fn.to_csv('false_negatives.csv', index=False)
print('Saved to false_negatives.csv')
"
```

### Step 2: Review False Negatives

1. Open `false_negatives.csv`
2. For each field, check:
   - Is the value actually in the PDF?
   - Is the value correct?
   - Why wasn't it marked as extracted?

### Step 3: Fix Extraction Logic

Update the test files to handle the identified cases:

```python
# In test files, update is_extracted logic
# Add special cases for identified false negatives
```

### Step 4: Re-run Tests

```bash
python run_comprehensive_extraction_tests.py
```

### Step 5: Compare Results

Compare before/after extraction rates to verify improvements.

## Best Practices

1. **Document False Negatives**: Keep a log of known false negatives and their causes
2. **Regular Reviews**: Periodically review extraction results for false negatives
3. **Field-Specific Rules**: Some fields may need special extraction logic
4. **Confidence Calibration**: Adjust confidence thresholds based on validation results
5. **Manual Spot Checks**: Manually verify a sample of "not extracted" fields

## Example: Fixing a Specific False Negative

If `gst_rate` is showing as not extracted but has value `5`:

1. **Check the CSV**: `gst_rate` has `llm_value=5` but `llm_extracted=False`
2. **Root Cause**: The value is `5` (not 0), so it should be extracted
3. **Fix**: The extraction logic might be checking for `Decimal('5.00')` vs `5`
4. **Solution**: Normalize numeric comparisons or adjust type checking

## Tools and Scripts

- `false_negatives_detector.py` - Automated false negative detection
- `field_validation.py` - Manual field validation tool
- `extraction_rate_calculator.py` - Adjusted extraction rate calculation
