# Address Extraction Fix Summary

## Problem Identified

Document Intelligence (DI) API was detecting address fields but not extracting their content, causing false negatives in the test results.

## Root Cause

1. **AddressValue Objects**: DI API returns `AddressValue` objects (from Azure SDK), not dictionaries. Our `_get_address` method only handled dicts and strings, so it returned `None` for `AddressValue` objects.

2. **Field Name Mismatch**: DI uses `BillingAddress` (not `CustomerAddress` or `BillToAddress`) for the bill-to address field. Our code was checking the wrong field names.

3. **Confidence Not Extracted**: The `_extract_field_confidences` method didn't handle `AddressValue` objects, so confidence scores weren't being extracted even when addresses had content.

## Fixes Applied

### 1. Updated `_get_address` method (`src/extraction/document_intelligence_client.py`)

**Before**: Only handled dicts and strings
```python
if isinstance(address_value, dict):
    # ... handle dict
elif isinstance(address_value, str):
    # ... handle string
return None  # AddressValue objects fell through here
```

**After**: Now handles `AddressValue` objects from Azure SDK
```python
# Handle AddressValue objects from Azure SDK
if hasattr(address_value, 'street_address') or hasattr(address_value, 'city'):
    # Extract attributes from AddressValue object
    address_dict = {
        "street_address": getattr(address_value, 'street_address', None),
        "city": getattr(address_value, 'city', None),
        "state": getattr(address_value, 'state', None),
        "postal_code": getattr(address_value, 'postal_code', None),
        # ... etc
    }
    # Build street_address from components if needed
    # Return dict if has content
```

### 2. Updated Field Name Mappings

**Before**: 
```python
"bill_to_address": self._get_address(fields, "CustomerAddress") or self._get_address(fields, "BillToAddress"),
```

**After**:
```python
"bill_to_address": self._get_address(fields, "BillingAddress") or self._get_address(fields, "CustomerAddress") or self._get_address(fields, "BillToAddress"),
```

Also updated `remit_to_address` to prioritize `RemittanceAddress`:
```python
"remit_to_address": self._get_address(fields, "RemittanceAddress") or self._get_address(fields, "RemitToAddress"),
```

### 3. Updated `_extract_field_confidences` method

**Before**: Only checked for dict and string types
```python
if isinstance(field.value, dict):
    # Check dict
elif isinstance(field.value, str):
    # Check string
```

**After**: Now handles `AddressValue` objects
```python
# Handle AddressValue objects from Azure SDK
if hasattr(field.value, 'street_address') or hasattr(field.value, 'city'):
    # Check if AddressValue has any non-empty attributes
    attrs_to_check = ['street_address', 'city', 'state', 'postal_code', ...]
    has_content = any(getattr(field.value, attr, None) for attr in attrs_to_check ...)
```

### 4. Updated Field Confidence Mapping (`src/extraction/field_extractor.py`)

Added mappings for DI field names:
```python
"BillingAddress": "bill_to_address",  # DI uses BillingAddress
"RemittanceAddress": "remit_to_address",  # DI uses RemittanceAddress
```

## Test Results

### Before Fix
- **VendorAddress**: Detected by DI (confidence 0.886) but not extracted
- **RemittanceAddress**: Detected by DI (confidence 0.886) but not extracted
- **BillingAddress**: Detected by DI (confidence 0.878) but not extracted
- All addresses showed as `None` in extraction results

### After Fix
- **VendorAddress**: ✅ Extracted with content (street_address, city, state, postal_code, country_region)
- **RemittanceAddress**: ✅ Extracted with content (po_box, city, state, postal_code)
- **BillingAddress**: ✅ Extracted with content (house_number, street_address, city, postal_code, country_region, level)

## AddressValue Object Structure

DI API returns `AddressValue` objects with these attributes:
- `house_number`: str or None
- `po_box`: str or None
- `road`: str or None
- `city`: str or None
- `state`: str or None
- `postal_code`: str or None
- `country_region`: str or None
- `street_address`: str or None (pre-combined)
- `unit`: str or None
- `level`: str or None
- `city_district`, `state_district`, `suburb`, `house`: str or None

## Impact

This fix should:
1. ✅ Extract addresses that DI successfully recognizes
2. ✅ Properly map confidence scores for address fields
3. ✅ Reduce false negatives in address field extraction
4. ✅ Improve extraction rate for documents with address information

## Next Steps

1. Re-run DI OCR tests to verify addresses are now extracted
2. Update false negative detection to account for successfully extracted addresses
3. Verify confidence scores are properly mapped and displayed
